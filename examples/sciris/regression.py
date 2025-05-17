"""
Can you add an example of how to do the linear regressions using sciris?
Change the timing functionality to use sciris.
"""
import numpy as np
import time

# Generate synthetic data
np.random.seed(42)
X = 2 * np.random.rand(1000, 1)
y = 4 + 3 * X + np.random.randn(1000, 1)

# Add bias term (intercept) to X
X_b = np.c_[np.ones((X.shape[0], 1)), X]

# Algorithm 1: Normal Equation
def normal_equation(X_b, y):
    return np.linalg.inv(X_b.T @ X_b) @ X_b.T @ y

# Algorithm 2: Gradient Descent
def gradient_descent(X_b, y, learning_rate=0.1, n_iterations=1000):
    m = X_b.shape[0]
    theta = np.random.randn(X_b.shape[1], 1)
    for iteration in range(n_iterations):
        gradients = 2/m * X_b.T @ (X_b @ theta - y)
        theta = theta - learning_rate * gradients
    return theta

# Time Normal Equation
start_time = time.time()
theta_normal = normal_equation(X_b, y)
normal_time = time.time() - start_time

# Time Gradient Descent
start_time = time.time()
theta_gd = gradient_descent(X_b, y)
gd_time = time.time() - start_time

# Output results
print("Normal Equation θ:", theta_normal.ravel())
print("Time taken (Normal Equation): {:.6f} seconds".format(normal_time))

print("Gradient Descent θ:", theta_gd.ravel())
print("Time taken (Gradient Descent): {:.6f} seconds".format(gd_time))
