import numpy as np
import time

from numpy import array as t_tensor
from sampling_methods.base import CSamplingMethod
from distributions.CMultivariateNormal import CMultivariateNormal
from utils.plot_utils import plot_pdf


class CLayeredAIS(CSamplingMethod):
    def __init__(self, space_min, space_max, params):
        """
        Implementation of Deterministic Mixture Adaptive Importance Sampling algorithm
        :param space_min: Space lower boundary
        :param space_max: Space upper boundary
        :param params:
            - K: Number of samples per proposal
            - N: Number of proposals
            - J: Maximum number of iterations when sampling
        """
        super(self.__class__, self).__init__(space_min, space_max)
        self.K = params["K"]
        self.N = params["N"]
        self.J = params["J"]
        self.L = params["L"]
        self.sigma = params["sigma"]
        self.mhsigma = params["mh_sigma"]
        self.mhproposal = CMultivariateNormal(np.zeros_like(self.space_max), np.diag(t_tensor([self.mhsigma] * len(self.space_max))))
        self.proposals = []
        self.reset()

    def reset(self):
        super(self.__class__, self).reset()

        # Reset the proposals
        self.proposals = []
        for _ in range(self.N):
            prop_center = np.random.uniform(self.space_min, self.space_max)
            prop_d = CMultivariateNormal(prop_center, np.diag(t_tensor([self.sigma] * len(self.space_max))))
            self.proposals.append(prop_d)

    def sample(self, n_samples):
        raise NotImplementedError

    def prob(self, s):
        prob = 0
        for q in self.proposals:
            prob += q.prob(s)
            self._num_q_evals += 1

        return prob / len(self.proposals)

    def mcmc_mh(self, x, prop_d, target_d, n_steps):
        for _ in range(n_steps):
            old_val = target_d.prob(x)
            x_hat = x + self.mhproposal.sample()
            new_val = target_d.prob(x_hat)
            alpha = np.random.rand()
            ratio = new_val / old_val

            x = x_hat if ratio > alpha else x
            prop_d.mean = x
        return prop_d.mean

    def resample(self, target_d):
        # Update all N proposals by performing L MCMC steps
        for prop_d in self.proposals:
            prop_d.mean = self.mcmc_mh(prop_d.mean, prop_d, target_d, self.L)

    def importance_sample(self, target_d, n_samples, timeout=60):
        elapsed_time = 0
        t_ini = time.time()

        while n_samples > len(self.samples) and elapsed_time < timeout:
            # Generate K samples from each proposal
            new_samples = t_tensor([])
            for q in self.proposals:
                for _ in range(self.K):
                    s = q.sample()
                    self._num_q_samples += 1

                    new_samples = np.concatenate((new_samples, s)) if new_samples.size else s

            # Weight samples
            new_weights = t_tensor([])
            for s in new_samples:
                w = target_d.prob(s) / self.prob(s)
                self._num_pi_evals += 1
                new_weights = np.concatenate((new_weights, w)) if new_weights.size else w

            # Adaptation
            self.resample(target_d)

            self.samples = np.concatenate((self.samples, new_samples)) if self.samples.size else new_samples
            self.weights = np.concatenate((self.weights, new_weights)) if self.weights.size else new_weights

            elapsed_time = time.time() - t_ini

        return self.samples, self.weights / self.weights.sum()

    def draw(self, ax):
        res = []
        for q in self.proposals:
            res.extend(ax.plot(q.mean.flatten(), 0, "gx", markersize=20))
            res.extend(plot_pdf(ax, q, self.space_min, self.space_max,
                                alpha=1.0, options="r--", resolution=0.01, scale=1/len(self.proposals)))

        for s, w in zip(self.samples, self.weights):
            res.append(ax.vlines(s, 0, w, "g", alpha=0.1))

        res.extend(plot_pdf(ax, self, self.space_min, self.space_max, alpha=1.0, options="r-", resolution=0.01))

        return res
