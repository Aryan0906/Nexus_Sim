#pragma once
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include "Quadtree.h" // QuadPoint<T>

namespace nexussim {

// Uniform spatial hash grid with a counting-sort build.
//
// The simulation rebuilds its spatial index every tick. A pointer-based
// quadtree costs ~1 us per insert because every subdivision reallocates and
// moves points; at 20k agents that alone was ~22 ms/tick. This grid builds in
// O(n + cells) with two reused buffers: count, prefix-sum, scatter. Points are
// stored contiguously per cell so radius queries have sequential locality.
//
// Query results are exact (post-filtered by squared distance), so it is a
// drop-in replacement for Quadtree::query_radius.
template <typename T = double>
class SpatialGrid {
public:
    // Keep the grid bounded regardless of city extent. Chicago's pseudo-meter
    // span is ~40 km, so cell_size is raised until <= 512x512 cells.
    static constexpr int kMaxAxisCells = 512;

    void rebuild(const std::vector<T>& xs,
                 const std::vector<T>& ys,
                 const std::vector<size_t>& indices,
                 T cell_size = static_cast<T>(30)) {
        n_ = xs.size();
        if (n_ == 0) {
            cols_ = rows_ = 0;
            cell_start_.clear();
            points_.clear();
            return;
        }

        T min_x = xs[0], max_x = xs[0];
        T min_y = ys[0], max_y = ys[0];
        for (size_t i = 1; i < n_; ++i) {
            min_x = std::min(min_x, xs[i]);
            max_x = std::max(max_x, xs[i]);
            min_y = std::min(min_y, ys[i]);
            max_y = std::max(max_y, ys[i]);
        }

        const T extent = std::max(max_x - min_x, max_y - min_y);
        cell_ = std::max(cell_size, extent / static_cast<T>(kMaxAxisCells));
        if (cell_ <= T(0)) cell_ = static_cast<T>(1);

        // Half-cell padding so points on the max edge have a valid cell.
        min_x_ = min_x - cell_ * static_cast<T>(0.5);
        min_y_ = min_y - cell_ * static_cast<T>(0.5);
        cols_ = static_cast<int>((max_x - min_x_) / cell_) + 1;
        rows_ = static_cast<int>((max_y - min_y_) / cell_) + 1;
        cols_ = std::max(1, std::min(cols_, kMaxAxisCells + 1));
        rows_ = std::max(1, std::min(rows_, kMaxAxisCells + 1));

        const size_t cells = static_cast<size_t>(cols_) * static_cast<size_t>(rows_);
        cell_start_.assign(cells + 1, 0);
        points_.resize(n_);
        cursor_.assign(cells, 0);

        for (size_t i = 0; i < n_; ++i)
            ++cell_start_[cell_index(xs[i], ys[i]) + 1];

        for (size_t c = 0; c < cells; ++c)
            cell_start_[c + 1] += cell_start_[c];

        for (size_t i = 0; i < n_; ++i) {
            const size_t c = cell_index(xs[i], ys[i]);
            points_[cell_start_[c] + cursor_[c]++] = QuadPoint<T>{xs[i], ys[i], indices[i]};
        }
    }

    void query_radius(T cx, T cy, T r,
                      std::vector<QuadPoint<T>>& out) const {
        if (n_ == 0 || cols_ == 0) return;

        int x0 = cell_coord(cx - r, min_x_, cols_);
        int x1 = cell_coord(cx + r, min_x_, cols_);
        int y0 = cell_coord(cy - r, min_y_, rows_);
        int y1 = cell_coord(cy + r, min_y_, rows_);
        if (x0 > x1 || y0 > y1) return;

        const T r2 = r * r;
        for (int gy = y0; gy <= y1; ++gy) {
            const size_t row = static_cast<size_t>(gy) * static_cast<size_t>(cols_);
            for (int gx = x0; gx <= x1; ++gx) {
                const size_t c = row + static_cast<size_t>(gx);
                const size_t begin = static_cast<size_t>(cell_start_[c]);
                const size_t end = static_cast<size_t>(cell_start_[c + 1]);
                for (size_t p = begin; p < end; ++p) {
                    const T dx = points_[p].x - cx;
                    const T dy = points_[p].y - cy;
                    if (dx * dx + dy * dy <= r2)
                        out.push_back(points_[p]);
                }
            }
        }
    }

    // Oriented capsule query: points with projection s in [0, forward] along
    // the unit direction (ux, uy) and |lateral| <= half_width. Used for
    // car-following lookahead: a 80m x 10m strip instead of an 80m-radius
    // circle, which scans ~25x fewer candidates in dense networks.
    void query_capsule(T cx, T cy, T ux, T uy, T forward, T half_width,
                       std::vector<QuadPoint<T>>& out) const {
        if (n_ == 0 || cols_ == 0) return;

        // AABB of the oriented rectangle: center, forward tip, and both
        // half-width offsets.
        const T px = -uy * half_width;
        const T py =  ux * half_width;
        const T fx = ux * forward;
        const T fy = uy * forward;
        const T xs[4] = {cx + px, cx - px, cx + fx + px, cx + fx - px};
        const T ys[4] = {cy + py, cy - py, cy + fy + py, cy + fy - py};
        T minx = xs[0], maxx = xs[0], miny = ys[0], maxy = ys[0];
        for (int k = 1; k < 4; ++k) {
            minx = std::min(minx, xs[k]);
            maxx = std::max(maxx, xs[k]);
            miny = std::min(miny, ys[k]);
            maxy = std::max(maxy, ys[k]);
        }

        const int x0 = cell_coord(minx, min_x_, cols_);
        const int x1 = cell_coord(maxx, min_x_, cols_);
        const int y0 = cell_coord(miny, min_y_, rows_);
        const int y1 = cell_coord(maxy, min_y_, rows_);

        for (int gy = y0; gy <= y1; ++gy) {
            const size_t row = static_cast<size_t>(gy) * static_cast<size_t>(cols_);
            for (int gx = x0; gx <= x1; ++gx) {
                const size_t c = row + static_cast<size_t>(gx);
                const size_t begin = static_cast<size_t>(cell_start_[c]);
                const size_t end = static_cast<size_t>(cell_start_[c + 1]);
                for (size_t p = begin; p < end; ++p) {
                    const T rx = points_[p].x - cx;
                    const T ry = points_[p].y - cy;
                    const T proj = rx * ux + ry * uy;
                    if (proj <= static_cast<T>(0.5) || proj > forward) continue;
                    const T perp = std::abs(-rx * uy + ry * ux);
                    if (perp > half_width) continue;
                    if (proj * proj + perp * perp > forward * forward) continue;
                    out.push_back(points_[p]);
                }
            }
        }
    }

    size_t point_count() const { return n_; }
    int cols() const { return cols_; }
    int rows() const { return rows_; }

private:
    int cell_coord(T v, T origin, int limit) const {
        int c = static_cast<int>((v - origin) / cell_);
        return std::max(0, std::min(c, limit - 1));
    }

    size_t cell_index(T x, T y) const {
        int gx = static_cast<int>((x - min_x_) / cell_);
        int gy = static_cast<int>((y - min_y_) / cell_);
        gx = std::max(0, std::min(gx, cols_ - 1));
        gy = std::max(0, std::min(gy, rows_ - 1));
        return static_cast<size_t>(gy) * static_cast<size_t>(cols_)
             + static_cast<size_t>(gx);
    }

    size_t n_ = 0;
    T min_x_ = 0, min_y_ = 0, cell_ = 1;
    int cols_ = 0, rows_ = 0;
    std::vector<int32_t> cell_start_; // size cells + 1
    std::vector<int32_t> cursor_;     // reused scatter buffer
    std::vector<QuadPoint<T>> points_;
};

} // namespace nexussim
