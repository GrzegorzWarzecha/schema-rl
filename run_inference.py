import os
from collections import deque
import numpy as np
from environment.schema_games.breakout.games import StandardBreakout
from model.featurematrix import FeatureMatrix
from model.inference import SchemaNetwork
from model.visualizer import Visualizer
from model.constants import Constants
from testing.testing import HardcodedSchemaVectors


class Runner(Constants):
    def __init__(self, n_episodes, n_steps, plan_every):
        self.n_episodes = n_episodes
        self.n_steps = n_steps
        self.plan_every = plan_every

    def load_schema_matrices(self, generate=True):
        if generate:
            W, R = HardcodedSchemaVectors.gen_schema_matrices()
        else:
            dir_name = './dump'
            W = []
            R = []
            for idx in range(self.M):
                file_name = 'w_{}'.format(idx)
                path = os.path.join(dir_name, file_name)
                w = np.load(path, allow_pickle=True)
                W.append(w)
            for idx in range(2):
                file_name = 'r_{}'.format(idx)
                path = os.path.join(dir_name, file_name)
                r = np.load(path, allow_pickle=True)
                R.append(r)
        return W, R

    def loop(self):
        W, R = self.load_schema_matrices()

        env = StandardBreakout()
        env.reset()

        visualizer = Visualizer(None, None, None)

        for episode_idx in range(self.n_episodes):
            frame_stack = deque(maxlen=self.FRAME_STACK_SIZE)
            actions = deque()

            for step_idx in range(self.n_steps):
                curr_iter = episode_idx * self.n_steps + step_idx

                obs = FeatureMatrix(env).matrix
                frame_stack.append(obs)

                # visualize env state
                visualizer.set_iter(curr_iter)
                visualizer.visualize_env_state(obs)

                if (step_idx - 1) % self.plan_every == 0 \
                        and len(frame_stack) >= self.FRAME_STACK_SIZE:
                    model = SchemaNetwork(W, R, frame_stack)
                    model.set_curr_iter(curr_iter)
                    planned_actions = model.plan_actions()
                    actions.clear()
                    actions.extend(planned_actions)

                if actions:
                    action = actions.popleft()
                else:
                    action = 0

                obs, reward, done, _ = env.step(action)
                if done:
                    print('END_OF_EPISODE, step_idx == {}'.format(step_idx))
                    break


def main():
    n_episodes = 8
    n_steps = 64
    plan_every = 30

    runner = Runner(n_episodes=n_episodes,
                    n_steps=n_steps,
                    plan_every=plan_every)
    runner.loop()


if __name__ == '__main__':
    main()
