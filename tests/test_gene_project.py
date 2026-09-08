import numpy as np

from speciesot.bundle import project_genes


def test_first_wins_and_zero_fill():
    names = ["ENSG1", "ENSG1", "ENSG2"]
    matrix = np.array([[1.0, 9.0, 2.0], [3.0, 8.0, 4.0]], dtype=np.float32)
    out = project_genes(matrix, names, ["ENSG1", "ENSG2", "ENSG_MISSING"])
    assert out.shape == (2, 3)
    np.testing.assert_array_equal(out[:, 0], [1.0, 3.0])
    np.testing.assert_array_equal(out[:, 1], [2.0, 4.0])
    np.testing.assert_array_equal(out[:, 2], [0.0, 0.0])


if __name__ == "__main__":
    test_first_wins_and_zero_fill()
    print("test_gene_project ok")
