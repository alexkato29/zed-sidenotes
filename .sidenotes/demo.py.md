@@ def matmul(a, b, n):
This function does a matrix multiply naively.

@@ c = [0.0] * (n * n)
This is to test adding a sidenote. 

@@ for k in range(n):
**Why i-k-j and not i-j-k**

- The inner loop walks `j`, so both `c[i*n + j]` and `b[k*n + j]` are unit-stride.
- With i-j-k the inner loop reads `b[k*n + j]` at stride `n`: one cache miss per
  iteration once `n` rows exceed L1.
- Unit stride also lets the hardware prefetcher lock on.

@@ aik = a[
Hoisted because the interpreter can't prove `a` isn't aliased by `c`, so it would
reload `a[i*n + k]` on every inner iteration.

```python
# what it would otherwise be doing
c[i*n + j] += a[i*n + k] * b[k*n + j]
```
