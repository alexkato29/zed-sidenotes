@@ for j in range(n):
We fill in one row of the output matrix `c` at a time. We scale row `b[k]` by the scalar
`a[i][k]` and add it into `c[i]`. After iterating through all pairs `(k, j)`, row `c[i]`
is complete. Functionally it's the dot product of row `a[i]` with every column of `b`.

But why `i, k, j` and not the textbook `i, j, k`? Hardware optimization. Caches grab 
lines, and they can only hold so many. If we walked the cols of `b` (and computed whole
elements of `c` at a time), we'd need `n + 1` cache lines (1 for `c`!) since a column of
`b` is not sequential in memory. While the next few columns would have their values 
preloaded into the cache, each `k` step only uses `2 / (n + 1)` of the lines. 
**Very low utilization.**

Going row by row, the cache line is immediately fully used, then can be discarded. We 
need `2 * sizeof(row) / 64` cache lines per `j` loop, and we use *all* of them.
**Very high utilization.**

(I am aware that using python lists destroys this intention, but it's a `demo.py` file 
for a code comment tool...)

@@ def matmul(a, b, n):
This function does a matrix multiply naively.
