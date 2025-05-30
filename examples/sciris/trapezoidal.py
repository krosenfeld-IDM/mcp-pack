"""
In this script can you also show how to do a simple numerical integration using sciris? Add it as one of the timed examples.
"""
import numpy as np
import time

def f(x):
    """Function to integrate."""
    return np.sin(x)

def trap_loop(f, a, b, n):
    """
    Pure‐Python rectangle (left Riemann) rule.
    O(n) in Python with Python‐level loop overhead.
    """
    h = (b - a) / n
    total = 0.0
    for i in range(n):
        total += f(a + i*h)
    return total * h

def trap_numpy(f, a, b, n):
    """
    NumPy vectorized trapezoidal rule.
    All heavy lifting in C; minimal Python overhead.
    """
    x = np.linspace(a, b, n)
    y = f(x)
    return np.trapz(y, x)

if __name__ == "__main__":
    a, b = 0.0, np.pi
    Ns = [10**4, 10**5, 10**6]

    print(f"{'n':>8s} | {'Loop Result':>12s} | {'Loop Time (s)':>14s} | {'NumPy Result':>12s} | {'NumPy Time (s)':>15s}")
    print("-" * 75)
    for n in Ns:
        # time pure‐Python loop
        t0 = time.perf_counter()
        res_loop = trap_loop(lambda x: np.sin(x), a, b, n)
        t_loop = time.perf_counter() - t0

        # time NumPy vectorized
        t0 = time.perf_counter()
        res_np = trap_numpy(np.sin, a, b, n)
        t_np = time.perf_counter() - t0

        print(f"{n:8d} | {res_loop:12.8f} | {t_loop:14.6f} | {res_np:12.8f} | {t_np:15.6f}")