import numpy as np
from scipy.optimize import linprog, minimize
from tqdm import tqdm
import torch
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable


def binarize(x):
    return 1 - ((x < 0.1) & (x > -0.1))


class SchemaNet:
    def __init__(self, N=0, M=53, A=2, L=5, window_size=2):
        self._M = M
        self.neighbour_num = (window_size * 2 + 1) ** 2
        print('neighbour_num_', self.neighbour_num)
        self._W = [np.zeros(self.neighbour_num * M + A) + 1] * M
        self.solved = np.array([])
        self._A = A
        self._L = L

        self.reward = []
        self.memory = []

    def log(self):
        print('current net shape:\n', [self._W[i].shape for i in range(len(self._W))])

    def print(self):
        print('current net:\n')
        for i in range(len(self._W)):
            print('   '*i, self._W[i].T)

    def predict_attr(self, X, i):
        X = np.array(X)
        if len(self._W[i].shape) == 1:
            return 1 - binarize((X == 0) @ self._W[i])
        #print('1', (1-binarize((X == 0) @ self._W[i])).any(axis=1) != 0)
        #print('0', (((X == 0) @ self._W[i]) == 1).any(axis=1) != 0)
        return (1 - binarize((X == 0) @ self._W[i])).any(axis=1) != 0

    def schema_predict_attr(self, X, i):
        return (1 - binarize((X == 0) @ self._W[i])) != 0

    def predict(self, X):
        return [self.predict_attr(X, i) for i in range(self._M)]

    def add(self, schemas, i):
        self._W[i] = np.vstack((self._W[i].T, schemas.T)).T

    def scipy_solve_lp(self, c, A_ub, b_ub, A_eq, b_eq, options={'maxiter': 2, "disp": False}):
        if len(A_eq) == 0:
            return linprog(c=c, A_eq=A_eq, b_eq=b_eq, options=options).x.round(2)
        else:
            return linprog(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, options=options).x.round(2)

    def torch_solve_lp(self, c, A_ub, b_ub, A_eq, b_eq, num_steps=20, p=3):

        torch_c = torch.tensor(c, dtype=torch.float32)
        torch_A_ub = torch.tensor(A_ub, dtype=torch.float32)
        torch_b_ub = torch.tensor(b_ub, dtype=torch.float32)
        torch_A_eq = torch.tensor(A_eq, dtype=torch.float32)
        torch_b_eq = torch.tensor(b_eq, dtype=torch.float32)

        '''torch_c = c
        torch_A_ub = A_ub
        torch_b_ub = b_ub
        torch_A_eq = A_eq
        torch_b_eq = b_eq'''

        INF = 10.

        starting_point = torch.tensor(np.zeros(len(c)), dtype=torch.float32)
        starting_point = Variable(starting_point, requires_grad=True)

        optimizer = optim.Adam([starting_point], lr=1e-1)

        def function_to_optim(x):
            # g = ().max()
            # A_ub * x <= b_ub
            # b_ub - A_ub * x >= 0
            # (max(0, -g_i))^p
            # g_i >= 0
            #
            g = (F.relu(torch_A_ub @ x - torch_b_ub)**p).sum()
            h = ((torch_A_eq @ x - torch_b_eq)**2).sum()
            #print('debug', g, h)
            return x @ torch_c + g + h

        for t in range(num_steps):
            optimizer.zero_grad()
            loss = function_to_optim(starting_point)
            loss.backward()
            optimizer.step()

        w = starting_point.detach().numpy()**2 > 0.5
        return w

    def get_not_predicted(self, X, y, i):
        self.remove_wrong_schemas(X, y)
        ind = (self.predict_attr(X, i) != y) | (y == 0)
        return X[ind], y[ind]

    def get_next_to_predict(self, X, y, i):

        print('yyyy', y, y.any())

        self.remove_wrong_schemas(X, y)

        print("PRED", self.predict_attr(X, i).any(), (self.predict_attr(X, i) != y).any(),  y.any())
        print(y)

        ind = (self.predict_attr(X, i) != y) * (y == 1)

        print('!!!!!!', self._W[i].shape, i, X[ind].shape)
        print(X[ind])


        if len(X[ind].shape) == 1:
            print(')', X[ind])
            return X[ind]

        if X[ind].shape[1] == 1:
            print(')', X[ind])
            return X[ind]

        return X[ind][0]

    def get_schema(self, X, y, i):

        zero_pred = X[y == 0]
        ones_pred = X[y == 1]
        print('y', y)

        self.solved = np.array([self.get_next_to_predict(X, y, i)])

        c = (1 - ones_pred).sum(axis=0)
        A_eq = 1 - self.solved
        b_eq = np.zeros(self.solved.shape[0])
        A_ub = zero_pred - 1
        b_ub = np.zeros(zero_pred.shape[0]) - 1

        w = self.torch_solve_lp(c, A_ub, b_ub, A_eq, b_eq)

        #print( '\nresult', 1 - binarize((X == 0) @ w))
        #print('\nwtf', (1 - self.solved)@w)

        preds = 1 - binarize((X == 0) @ w)
        #print('Preds', X[preds])
        #print('check', preds * (self.predict_attr(X, i) == 0))
        #print((self.predict_attr(X, i) == 0)*preds)
        ind = (preds * (self.predict_attr(X, i) == 0)) == 1

        print(X[ind].shape, self.solved.shape)
        #print(self.solved[0])
        self.solved = np.vstack((self.solved, X[ind]))
        #print(self.solved)
        return w

    def simplify_schema(self, X, y):

        zero_pred = X[y == 0]

        c = np.zeros(self.neighbour_num * self._M + self._A)
        A_eq = (1 - self.solved)
        b_eq = np.zeros(self.solved.shape[0])
        print('A', A_eq)
        A_ub = (zero_pred - 1)
        b_ub = np.zeros(zero_pred.shape[0]) - 1
        w = self.torch_solve_lp(c, A_ub, b_ub, A_eq, b_eq)

        #print('WTF', 1 - binarize((X == 0) @ w))
        #print(w)

        return w

    def actuality_check_attr(self, X, y, i):
        if len(self._W[i].shape) == 1:
            return np.zeros(self._W[i].shape[0])
        pred = self.schema_predict_attr(X, i).T
        return ((y[i] - pred) == -1)

    def remove_wrong_schemas(self, X, y):
        for i in range(self._M):
            if len(self._W[i].shape) == 1:
                break
            wrong_ind = self.actuality_check_attr(X, y, i).sum(axis=1)

            if (wrong_ind == 0).sum() != 0:
                print('outdated schema was detected for attribute', i)

            self._W[i] = (self._W[i].T[wrong_ind == 0]).T

    def fit(self, X, Y, log=True):

        ind = X.sum(axis=1) > 0
        X = X[ind]
        Y = (Y.T[ind]).T

        self.remove_wrong_schemas(X, Y)

        for i in tqdm(range(self._M)):

            for j in tqdm(range(self._L)):

                if (self.predict_attr(X, i) == Y[i]).all():
                    if log:
                        print('all attrs are predicted for attr', i)
                    break

                x, y = self.get_not_predicted(X, Y[i], i)

                w = binarize(self.get_schema(x, y, i))
                #print('w:', w)
                w = (self.simplify_schema(x, y) > 0.1) * 1
                #print('w sipled', w_)
                self.add(w, i)
                if log:
                    self.log()


if __name__ == '__main__':
    X = np.array([[0, 1, 0, 1, 0, 0],
                  [0, 1, 1, 0, 0, 0],
                  [0, 0, 0, 0, 1, 0],
                  [1, 1, 1, 0, 0, 0],
                  [0, 0, 0, 1, 1, 0]])

    y = np.array([[0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0],
                  [1, 0, 0, 0, 1]])
    schemanet = SchemaNet(M=6, A=0, window_size=0)
    schemanet.fit(X, y)


    schemanet.print()
    schemanet.remove_wrong_schemas(X, y)
    print('?????', schemanet.actuality_check_attr(X, y, 5))
    schemanet.print()
