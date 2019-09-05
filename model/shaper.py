import numpy as np
from .constants import Constants


class Shaper(Constants):
    def __init__(self):

        # N x (R-1)
        # using (N+1) as invalid index to prevent blanks during filling matrix in
        self._ne_entity_indices = np.full((self.N, self.NEIGHBORS_NUM), self.N + 1, dtype=int)
        self._gen_ne_entity_indices()

        # indices of ne_indices are indexing (N x M) matrix only by rows!
        # using (N+1) for enlarged size with fake entity having latest index
        # self._ne_unravelled_indices = np.unravel_index(self._ne_entity_indices, self.N + 1)

    def _transform_pos_to_idx(self, pos):
        """
        :param pos: tuple of (row_idx, col_idx)
        :return: idx of pixel that runs by rows left2right
        """
        i, j = pos
        return i * self.SCREEN_WIDTH + j

    def _transform_idx_to_pos(self, idx):
        """
        :param idx: idx of pixel that runs by rows left2right
        :return: tuple of (row_idx, col_idx)
        """
        i = idx // self.SCREEN_WIDTH
        j = idx % self.SCREEN_WIDTH
        return (i, j)

    def _gen_ne_entity_indices(self):
        """
        """
        for entity_idx in range(self.N):
            row, col = self._transform_idx_to_pos(entity_idx)
            ne_turn = 0
            for i in range(-self.NEIGHBORHOOD_RADIUS, self.NEIGHBORHOOD_RADIUS + 1):
                ne_row = row + i

                for j in range(-self.NEIGHBORHOOD_RADIUS, self.NEIGHBORHOOD_RADIUS + 1):
                    if i == 0 and j == 0:
                        continue

                    ne_col = col + j
                    if (ne_row < 0 or ne_row >= self.SCREEN_HEIGHT
                            or ne_col < 0 or ne_col >= self.SCREEN_WIDTH):
                        ne_idx = self.FAKE_ENTITY_IDX
                    else:
                        ne_idx = self._transform_pos_to_idx((ne_row, ne_col))

                    self._ne_entity_indices[entity_idx, ne_turn] = ne_idx
                    ne_turn += 1

    def _get_ne_matrix(self, src_matrix, matrix_type):
        """
        :param src_matrix: (N x M)
        :return: (N x M(R-1))
        """
        assert (matrix_type in ('numbers', 'nodes'))
        filler_type = 'zero' if matrix_type == 'numbers' else 'none'
        augmented_matrix = self._augment_matrix(src_matrix, filler_type)

        ne_matrix = augmented_matrix[self._ne_entity_indices, :] \
            .reshape(self.N, self.M * self.NEIGHBORS_NUM)
        return ne_matrix

    def _augment_matrix(self, matrix, filler):
        assert (filler is False or filler is None)
        last_row = np.full(
            matrix.shape[1], filler
        )
        augmented_matrix = np.vstack(
            (matrix, last_row)
        )
        return augmented_matrix

    def _get_action_matrix(self):
        action_matrix = np.full((self.N, self.ACTION_SPACE_DIM), True, dtype=bool)
        return action_matrix

    def transform_matrix(self, src_matrix):
        """
        convert (N x M) to (N x (MR + A))
        """
        ne_matrix = self._get_ne_matrix(src_matrix, matrix_type='numbers')
        action_matrix = self._get_action_matrix()

        transformed_matrix = np.hstack(
            (src_matrix, ne_matrix, action_matrix)
        )
        return transformed_matrix

    def _get_node_action_matrix(self, action_nodes, t):
        node_action_matrix = np.full(
            (self.N, self.ACTION_SPACE_DIM), None, dtype=object
        )
        node_action_matrix[:, :] = action_nodes[t, :]
        return node_action_matrix

    def transform_node_matrix(self, src_matrix, action_nodes, t):
        """
        convert (N x M) to (N x (MR + A))
        """
        ne_matrix = self._get_ne_matrix(src_matrix, matrix_type='nodes')
        action_matrix = self._get_node_action_matrix(action_nodes, t)

        transformed_matrix = np.hstack(
            (src_matrix, ne_matrix, action_matrix)
        )
        return transformed_matrix





