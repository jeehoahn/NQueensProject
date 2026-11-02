"""Six variants: center-out clockwise spiral order, bitmask and/or symmetry."""
from algorithms.registry import AlgorithmRegistry
from algorithms.implementations.backtracking.variant_engine import ConfiguredStackDFS


class CenterStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "center_stack"
    display_name = "중앙 시작 달팽이 · 스택 DFS"
    spiral_order = True


class BitStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "bit_stack"
    display_name = "첫 퀸 이후 비트마스크 · 스택 DFS"
    bit_optimized = True


class CenterBitStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "center_bit_stack"
    display_name = "중앙 시작 달팽이 · 비트마스크 스택 DFS"
    spiral_order = True
    bit_optimized = True


class SymmetricStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "symmetric_stack"
    display_name = "스택 DFS · 대칭성 제거"
    remove_symmetry = True


class SymmetricBitStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "symmetric_bit_stack"
    display_name = "첫 퀸 이후 비트마스크 DFS · 대칭성 제거"
    bit_optimized = True
    remove_symmetry = True


class CenterSymmetricBitStackBacktracking(ConfiguredStackDFS):
    algorithm_id = "center_symmetric_bit_stack"
    display_name = "중앙 시작 달팽이 · 비트마스크 DFS · 대칭성 제거"
    spiral_order = True
    bit_optimized = True
    remove_symmetry = True


for implementation in (
    CenterStackBacktracking, BitStackBacktracking, CenterBitStackBacktracking,
    SymmetricStackBacktracking, SymmetricBitStackBacktracking,
    CenterSymmetricBitStackBacktracking,
):
    AlgorithmRegistry.register(implementation)
