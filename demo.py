def matmul(a, b, n):
    c = [0.0] * (n * n)
    for i in range(n):
        for k in range(n):
            aik = a[i * n + k]
            for j in range(n):
                c[i * n + j] += aik * b[k * n + j]
    return c
