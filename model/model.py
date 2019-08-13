import numpy as np
#from featurematrix import FeatureMatrix


class SchemaNetwork:
    def __init__(self, N, M, A, L, T):
        """
        N: number of entities
        M: number of attributes of each entity
        A: number of available actions
        L: number of schemas
        T: size of look-ahead window
        required_actions: actions agent should take to reach planned reward
        """
        self._N = N
        self._M = M
        self._A = A
        self._L = L
        self._T = T

        # list of M matrices, each of [(MR + A) x L] shape
        self._W = []

        # list of 2 matrices, each of [(MN + A) x L] shape
        # first - positive reward
        # second - negative reward
        self._R = []

        self.required_actions = []

    def _reset_actions(self):
        self.required_actions.clear()

    def _predict_next_attributes(self, X):
        """
        X: matrix of entities, [N x (MR + A)]
        """
        # check dimensions
        assert (X.shape == (self._N, (self._M * self._R + self._A)))
        for W in self._W:
            assert (W.shape[0] == (self._M * self._R + self._A))
            assert (W.dtype == bool)

        # expecting (N x M) matrix
        prediction = np.zeros((self._N, self._M))
        for idx, W in enumerate(self._W):
            prediction_matrix = ~(~X @ W)
            prediction[:idx] = prediction_matrix.sum(axis=1)

        return prediction

    def _predict_next_rewards(self, X):
        """
        X: vector of all attributes and actions, [1 x (NM + A)]
        """
        # check dimensions
        assert (X.shape == (1, (self._N * self._M + self._A)))
        for R in self._R:
            assert (R.shape == ((self._N * self._M + self._A), self._L))
            assert (R.dtype == bool)

        # expecting 2 rewards: pos and neg
        predictions = []
        for R in self._R:
            prediction = ~(~X @ R)
            predictions.append(prediction)

        return tuple(predictions)

    def _forward_pass(self, X, V):
        """
        X: matrix [N x (MR + A)]
        V: matrix [1 x (MN + A)]
        """
        current_X = X
        current_V = V
        for t in range(self._T):
            next_X = self._predict_next_attributes(current_state)
            # have no X to predict further
            # to construct it we need to measure distance between entities (to make [MR] part of the vector)
            # we need position attributes!

    def _backtrace_schema(self, schema):
        """
        Determines if schema is reachable
        Keeps track of action path

        is_reachable: can it be certainly activated given the state at t = 0
        """

        # lazy combining preconditions by AND -> assuming True
        schema.is_reachable = True

        for precondition in schema.attribute_preconditions:
            if precondition.is_reachable is None:
                # this node is NOT at t = 0 AND we have not computed it's value
                # dfs over precondition's schemas
                self._backtrace_attribute(precondition)
            if not precondition.is_reachable:
                # schema can *never* be reachable, break and try another schema
                schema.is_reachable = False
                break

    def _backtrace_attribute(self, node):
        """
        Determines if node is reachable

        is_reachable: can it be certainly activated given the state at t = 0
        """

        # lazy combining schemas by OR -> assuming False
        node.is_reachable = False

        for schema in node.schemas:
            if schema.is_reachable is None:
                self._backtrace_schema(schema)

            if schema.is_reachable:
                # attribute is reachable by this schema
                self.required_actions.append(schema.action_preconditions)
                break
            else:
                self._reset_actions()#???

