import numpy as np
import time
from sampling_methods.base import CSamplingMethod


class CNestedSampling(CSamplingMethod):
    def __init__(self, space_min, space_max, proposal_dist, num_points):
        super(self.__class__, self).__init__(space_min, space_max)
        self.range = space_max - space_min
        self.proposal_dist = proposal_dist
        self.N = num_points

        # Obtain initial samples from a uniform prior distribution
        self.live_points = np.random.uniform(0, 1, size=(self.N, len(self.space_max))) * self.range + self.space_min

    def sample(self, n_samples):
        raise NotImplementedError

    def reset(self):
        self.live_points = np.random.uniform(0, 1, size=(self.N, len(self.space_max))) * self.range + self.space_min

    def resample(self, sample, value, pdf, timeout=60):
        new_sample = self.proposal_dist.sample() + sample
        new_value = pdf.log_prob(new_sample)
        elapsed_time = 0
        t_ini = time.time()
        while value > new_value and elapsed_time < timeout:
            new_sample = self.proposal_dist.sample() + sample
            new_value = pdf.log_prob(new_sample)
            elapsed_time = time.time() - t_ini
        return new_sample, new_value

    def sample_with_likelihood(self, pdf, n_samples, timeout=60):
        points = self.live_points
        values = pdf.log_prob(points)
        samples = np.array([])

        L = np.zeros(n_samples)
        X = np.zeros(n_samples)
        W = np.zeros(n_samples)
        Z = 0
        for i in range(n_samples):
            L[i] = np.min(values)
            X[i] = np.exp(-i / self.N)
            W[i] = X[i-1] - X[i]
            Z = Z + L[i] * W[i]

            # Add the point with lowest likelihood to the resulting sample set
            min_idx = np.argmin(values)
            samples = np.concatenate((samples, points[min_idx]))

            # Replace the point with lowest likelihood with a new sample from the proposal distribution
            points[min_idx], values[min_idx] = self.resample(points[min_idx], L[i], pdf, timeout)

        samples = samples.reshape(n_samples, -1)
        values = pdf.log_prob(samples)
        return samples, values