import numpy as np
from .constants import Constants
from .graph_utils import Schema, Node, Attribute, Action, Reward
from .tensor_handler import TensorHandler
from .planner import Planner
from .visualizer import Visualizer


class SchemaNetwork(Constants):
    def __init__(self, W, R, proxy_env):
        """
        :param W: list of M matrices, each of [(MR + A) x L] shape
        :param R: list of 2 matrices, each of [(MN + A) x L] shape, 1st - pos, 2nd - neg
        """
        self._assert_input(W, R)

        self._W = W
        self._R = R

        self._print_input_stats()

        self._attribute_nodes = None  # tensor ((FRAME_STACK_SIZE + T) x N x M)
        self._action_nodes = None  # tensor ((FRAME_STACK_SIZE + T) x ACTION_SPACE_DIM)
        self._reward_nodes = None  # tensor ((FRAME_STACK_SIZE + T) x REWARD_SPACE_DIM)

        self._gen_attribute_nodes()
        self._gen_action_nodes()
        self._gen_reward_nodes()

        self._tensor_handler = TensorHandler(self._W, self._R, self._attribute_nodes,
                                             self._action_nodes, self._reward_nodes,
                                             proxy_env)
        self._planner = Planner(self._reward_nodes)
        self._visualizer = Visualizer(self._W)
        self._iter = None

    def _assert_input(self, W, R):
        required_matrix_shape = (self.N_COLS_TRANSFORMED, self.L)
        for matrix in (W + R):
            assert matrix.dtype == bool, 'BAD_MATRIX_DTYPE'
            assert matrix.ndim == 2, 'BAD_MATRIX_NDIM'
            assert (matrix.shape[0] == required_matrix_shape[0]
                    and matrix.shape[1] <= required_matrix_shape[1]), 'BAD_MATRIX_SHAPE'

    def _print_input_stats(self):
        print('Constructing SchemaNetwork object...')
        print('Numbers of schemas in W are: ', end='')
        for idx, w in enumerate(self._W):
            print('{}'.format(w.shape[1]), end='')
            if idx != len(self._W) - 1:
                print(' / ', end='')
        print()

    def set_curr_iter(self, iter):
        self._iter = iter

    def _gen_attribute_node_matrix(self, t):
        n_rows = self.N
        n_cols = self.M
        is_active = True if t < self.FRAME_STACK_SIZE else False
        matrix = [
            [Attribute(entity_idx, attribute_idx, t, is_active) for attribute_idx in range(n_cols)]
            for entity_idx in range(n_rows)
        ]
        return matrix

    def _gen_attribute_nodes(self):
        tensor = [self._gen_attribute_node_matrix(t) for t in range(self.FRAME_STACK_SIZE + self.T)]
        self._attribute_nodes = np.array(tensor)

    def _gen_action_nodes(self):
        action_nodes = [
            [Action(idx, t=t) for idx in range(self.ACTION_SPACE_DIM)]
            for t in range(self.FRAME_STACK_SIZE + self.T)
        ]
        self._action_nodes = np.array(action_nodes)

    def _gen_reward_nodes(self):
        reward_nodes = [
            [Reward(idx, t=t) for idx in range(self.REWARD_SPACE_DIM)]
            for t in range(self.FRAME_STACK_SIZE + self.T)
        ]
        self._reward_nodes = np.array(reward_nodes)

    def plan_actions(self):
        # stub for proxy_env list of objects
        if len(self._tensor_handler._proxy_env) < self.FRAME_STACK_SIZE:
            print('Small proxy_env len, can\'t plan, returning random actions.')
            planned_actions = np.random.randint(low=0,
                                                high=self.ACTION_SPACE_DIM,
                                                size=self.T)
            return planned_actions

        # instantiate schemas, determine nodes feasibility
        attribute_tensor = self._tensor_handler.forward_pass()

        # generate images of inner state here
        self._visualizer.set_attribute_tensor(attribute_tensor, self._iter)
        self._visualizer.visualize_inner_state(check_correctness=True)

        # planning actions
        actions = self._planner.plan_actions()

        return actions
