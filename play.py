import os
from collections import deque
import time
import numpy as np
from environment.schema_games.breakout.games import StandardBreakout, OffsetPaddleBreakout, JugglingBreakout
from model.entity_extractor import EntityExtractor
from model.inference import SchemaNetwork
from model.visualizer import Visualizer
from model.constants import Constants
from testing.testing import HardcodedSchemaVectors
from model.schema_learner import GreedySchemaLearner
from model.shaper import Shaper


class DataLoader(Constants):
    def __init__(self, shaper):
        self._shaper = shaper

    def make_batch(self, observations, actions):
        frame_stack = [observations[idx] for idx in range(self.FRAME_STACK_SIZE)]
        action = actions[self.FRAME_STACK_SIZE - 1]
        augmented_entities = self._shaper.transform_matrix(frame_stack, action=action)
        target = observations[self.FRAME_STACK_SIZE][:, :self.N_PREDICTABLE_ATTRIBUTES]
        batch = GreedySchemaLearner.Batch(augmented_entities, target)
        return batch


class Runner(Constants):
    env_type_to_class = {
        'standard': StandardBreakout,
        'offset-paddle': OffsetPaddleBreakout,
        'juggling': JugglingBreakout
    }
    env_params = {
        'report_nzis_as_entities': 'all',
        'num_lives': 10 ** 9 + 7
    }

    def __init__(self, env_type, n_episodes, n_steps):
        self.env_class = self.env_type_to_class[env_type]
        self.n_episodes = n_episodes
        self.n_steps = n_steps

        # stuff for hardcoded action
        self._paddle_keypoint_idx = None
        self._keypoint_timer = None
        self.KEYPOINT_TIMER = 30

    def _get_hardcoded_action(self, env, eps=0.0):
        if np.random.uniform() < eps:
            chosen_action = np.random.choice(self.ACTION_SPACE_DIM)
        else:
            ball_x = EntityExtractor.get_ball_x(env)
            targets = EntityExtractor.get_paddle_keypoints(env)

            if not self._keypoint_timer:
                self._paddle_keypoint_idx = np.random.choice(len(targets))
                self._keypoint_timer = self.KEYPOINT_TIMER
            else:
                self._keypoint_timer -= 1

            target = targets[self._paddle_keypoint_idx]
            if ball_x < target:
                chosen_action = 1
            elif ball_x > target:
                chosen_action = 2
            else:
                chosen_action = 0

        return chosen_action

    def load_schema_matrices(self):
        if not self.USE_LEARNED_SCHEMAS:
            W, R, R_weights = HardcodedSchemaVectors.gen_schema_matrices()
        else:
            dir_name = './dump'
            W = []
            R = []
            R_weights = None
            for idx in range(self.M - 1):
                file_name = 'w_{}.pkl'.format(idx)
                path = os.path.join(dir_name, file_name)
                w = np.load(path, allow_pickle=True).astype(bool)
                W.append(w)

            #for idx in range(1):
             #   file_name = '_schemas_standardreward/schema{}.txt'.format(idx)
             #   path = os.path.join(dir_name, file_name)
             #   r = np.loadtxt(path).astype(bool)
             #   R.append(r)

            _, R, _ = HardcodedSchemaVectors.gen_schema_matrices()
        return W, R, R_weights

    def loop(self):
        _, R, _ = self.load_schema_matrices()

        env = self.env_class(**self.env_params)
        shaper = Shaper()
        visualizer = Visualizer(None, None, None)
        data_loader = DataLoader(shaper)
        learner = GreedySchemaLearner()
        planner = SchemaNetwork()

        env.reset()

        for episode_idx in range(self.n_episodes):
            observations = deque(maxlen=self.LEARNING_BATCH_SIZE)
            frame_stack = deque(maxlen=self.FRAME_STACK_SIZE)

            actions_taken = deque(maxlen=self.LEARNING_BATCH_SIZE)
            exec_actions = deque()

            emergency_replanning_timer = None

            for step_idx in range(self.n_steps):
                curr_iter = episode_idx * self.n_steps + step_idx
                print('\ncurr_iter: {}'.format(curr_iter))

                obs = EntityExtractor.extract(env)
                observations.append(obs)
                frame_stack.append(obs)

                if self.VISUALIZE_STATE:
                    # visualize env state
                    visualizer.set_iter(curr_iter)
                    visualizer.visualize_env_state(obs)

                # --- planning ---

                W = learner.get_weights()

                can_run_planner = W is not None and len(frame_stack) == self.FRAME_STACK_SIZE
                is_planning_needed = len(exec_actions) == 0 and emergency_replanning_timer is None \
                                     or emergency_replanning_timer == 0

                if is_planning_needed and can_run_planner:
                    print('Launching planning procedure...')
                    emergency_replanning_timer = None

                    planner.set_weights(W, R)
                    planner.set_curr_iter(curr_iter)

                    planned_actions = planner.plan_actions(frame_stack)
                    if planned_actions is not None:
                        exec_actions.clear()
                        exec_actions.extend(planned_actions)

                if exec_actions:
                    chosen_action = exec_actions.popleft()
                else:
                    chosen_action = np.random.choice(self.ACTION_SPACE_DIM)

                    if can_run_planner:
                        if emergency_replanning_timer is None:
                            emergency_replanning_timer = self.EMERGENCY_REPLANNING_PERIOD
                        emergency_replanning_timer -= 1
                # ---------------------

                actions_taken.append(chosen_action)

                # --- learning ---
                if len(observations) >= self.LEARNING_BATCH_SIZE:
                    print('adding batch to learner')
                    batch = data_loader.make_batch(observations, actions_taken)

                    learner.set_curr_iter(curr_iter)
                    learner.take_batch(batch)

                    is_flush_needed = curr_iter == self.n_episodes * self.n_steps - 1
                    if curr_iter % self.LEARNING_PERIOD == 0 or is_flush_needed:
                        print('Launching learning procedure...')
                        learner.learn()

                obs, reward, done, _ = env.step(chosen_action)
                if done:
                    print('END_OF_EPISODE, step_idx == {}'.format(step_idx))
                    break


def main():
    n_episodes = 3
    n_steps = 10000
    env_type = 'standard'
    assert env_type in ('standard', 'offset-paddle', 'juggling')

    runner = Runner(env_type=env_type,
                    n_episodes=n_episodes,
                    n_steps=n_steps)
    runner.loop()


if __name__ == '__main__':
    main()
