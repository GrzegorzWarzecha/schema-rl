import numpy as np
from scipy.optimize import linprog
import os
from termcolor import colored
from model.constants import Constants


class SchemaNet(Constants):
    def __init__(self):
        self.neighbour_num = ((self.NEIGHBORHOOD_RADIUS * 2 + 1) ** 2) * self.FRAME_STACK_SIZE
        self._W = [np.zeros([self.neighbour_num * self.M + self.ACTION_SPACE_DIM, 1]) + 1] * self.M
        self.solved = np.array([])
        self._R = [np.zeros(self.neighbour_num * self.M + self.ACTION_SPACE_DIM) + 1] * 2

    def log(self):
        print('current net:\n', [self._W[i].shape for i in range(len(self._W))])

    def print(self):
        print('current net:\n')
        for i in range(len(self._W)):
            print('   ' * i, self._W[i].T)

    def _predict_attr(self, X, i):
        if len(self._W[i].shape) == 1:
            return (X == 0) @ self._W[i] == 0
        return ((X == 0) @ self._W[i] == 0).any(axis=1) != 0

    def _schema_predict_attr(self, X, i):
        return ((X == 0) @ self._W[i] == 0) != 0

    '''def _predict_reward(self, X, is_pos=1):
        if len(self._R[is_pos].shape) == 1:
            return (X == 0) @ self._R[is_pos] == 0
        return ((X == 0) @ self._R[is_pos] == 0).any(axis=1) != 0'''

    def predict(self, X):
        return np.array([self._predict_attr(X, i) for i in range(self.M)])

    def add(self, schemas, i):
        self._W[i] = np.vstack((self._W[i].T, schemas.T)).T

    def scipy_solve_lp(self, zero_pred, c, A_ub, b_ub, A_eq, b_eq, options={'maxiter': 2, "disp": False}):
        if len(zero_pred) == 0:
            return linprog(c=c, A_eq=A_eq, b_eq=b_eq, options=options).x.round(2)
        else:
            return linprog(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, options=options).x.round(2)

    def _get_not_predicted(self, X, y, i):
        ind = (self._predict_attr(X, i) != y) | (y == 0)
        return X[ind], y[ind]

    '''def reverse_transform_print(self, y):

        for i in range(self.NEIGHBORHOOD_RADIUS * 2 + 1):
            for j in range(self.NEIGHBORHOOD_RADIUS * 2 + 1):
                ind = i * (self.NEIGHBORHOOD_RADIUS * 2 + 1) * 4 + j * 4
                if y[ind] == 1:
                    print(colored('*', 'red'), end='')
                elif y[ind + 1] == 1:
                    print(colored('*', 'cyan'), end='')
                elif y[ind + 2] == 1:
                    print(colored('*', 'green'), end='')
                elif y[ind + 3] == 1:
                    print(colored('*', 'grey'), end='')
                else:
                    print(colored('*', 'white'), end='')
            print()

    def visualize_schemas(self):
        for W in self._W:
            print('#' * 50)
            for schema in W.T:
                self.reverse_transform_print(schema[:100])
                print(' ' * 50)
                self.reverse_transform_print(schema[100:])
                print('-' * 50)
    '''

    def _get_next_to_predict(self, X, y, i, log=False):
        ind = (self._predict_attr(X, i) != y) * (y == 1)

        if ind.sum() == 0:
            print(colored('FATAL ERROR', 'red'))
            return None
        result = X[ind][0]
        return result

    def _get_schema(self, X, y, i, log=True):

        zero_pred = X[y == 0]
        ones_pred = X[y == 1]

        new_ent = self._get_next_to_predict(X, y, i, log=log)
        self.solved = np.array([new_ent])

        c = (1 - ones_pred).sum(axis=0)
        A_eq = 1 - self.solved
        b_eq = np.zeros(self.solved.shape[0])
        A_ub = zero_pred - 1
        b_ub = np.zeros(zero_pred.shape[0]) - 1
        w = self.scipy_solve_lp(zero_pred, c, A_ub, b_ub, A_eq, b_eq)

        preds = ((X == 0) @ w) == 0
        self.solved = np.vstack((self.solved, X[preds * (self._predict_attr(X, i) == 0)]))
        return w

    def _simplify_schema(self, X, y):

        zero_pred = X[y == 0]

        c = np.zeros(self.neighbour_num * self.M + self.ACTION_SPACE_DIM)
        A_eq = (1 - self.solved)
        b_eq = np.zeros(self.solved.shape[0])
        A_ub = (zero_pred - 1)
        b_ub = np.zeros(zero_pred.shape[0]) - 1

        return self.scipy_solve_lp(zero_pred, c, A_ub, b_ub, A_eq, b_eq)

    def _actuality_check_attr(self, X, y, i):
        if len(self._W[i].shape) == 1:
            return np.zeros(self._W[i].shape[0])
        pred = self._schema_predict_attr(X, i).T
        return ((y[i] - pred) == -1)

    def _remove_wrong_schemas(self, X, y):
        for i in range(self.M):
            if len(self._W[i].shape) == 1:
                break
            wrong_ind = self._actuality_check_attr(X, y, i).sum(axis=1)

            if (wrong_ind.sum()) != 0:
                print('outdated schema was detected for attribute', i)

            self._W[i] = (self._W[i].T[wrong_ind == 0]).T

    def fit(self, X, Y, log=True):
        tmp, ind = np.unique(X, return_index=True, axis=0)
        X = X[ind]

        print('index shape', ind.shape)

        Y = (Y.T[ind]).T

        self._remove_wrong_schemas(X, Y)

        for i in (range(self.M)):

            for j in (range(self.L)):

                if isinstance((self._predict_attr(X, i) == Y[i]), np.ndarray):
                    if (self._predict_attr(X, i) == Y[i]).all():
                        if log:
                            if i == 0:
                                print('ball check', (self._predict_attr(X, i) == 1).any(), (Y[i] == 1).any())

                            print('all attrs are predicted for attr', i)
                        break
                else:
                    if self._predict_attr(X, i) == Y[i]:
                        if log:
                            print('all attrs are predicted for attr', i)
                        break

                x, y = self._get_not_predicted(X, Y[i], i)

                self._get_schema(x, y, i)
                w = (self._simplify_schema(x, y) > 0.1).astype(np.bool, copy=False)
                self.add(w, i)
                if log:
                    self.log()

    def save(self, type_name='standard', is_reward=''):
        path = '_schemas_' + type_name + is_reward
        if not os.path.exists(path):
            os.makedirs(path)
        for i in range(self.M):
            np.savetxt(path + '/schema' + str(i) + '.txt', self._W[i])

    def load(self, type_name='standard'):
        for i in range(self.M):
            schema = np.loadtxt('_schemas_' + type_name + '/schema' + str(i) + '.txt')
            self._W[i] = schema
