import numpy as np
from model.constants import Constants


class EntityExtractor(Constants):
    @classmethod
    def extract(cls, env):
        """
        :param env: object, child of BreakoutEngine
        """
        matrix = np.zeros((cls.N, cls.M), dtype=bool)

        for ball in env.balls:
            if ball.is_entity:
                for state, eid in env.parse_object_into_pixels(ball):
                    idx = cls.get_entity_idx(state)
                    matrix[idx][cls.BALL_IDX] = True

        if env.paddle.is_entity:
            for state, eid in env.parse_object_into_pixels(env.paddle):
                idx = cls.get_entity_idx(state)
                matrix[idx][cls.PADDLE_IDX] = True

        for wall in env.walls:
            if wall.is_entity:
                for state, eid in env.parse_object_into_pixels(wall):
                    idx = cls.get_entity_idx(state)
                    matrix[idx][cls.WALL_IDX] = True

        for brick in env.bricks:
            if brick.is_entity:
                for state, eid in env.parse_object_into_pixels(brick):
                    idx = cls.get_entity_idx(state)
                    matrix[idx][cls.BRICK_IDX] = True

        # raise VOID bit
        void_mask = ~matrix.any(axis=1)
        matrix[void_mask, cls.VOID_IDX] = True

        return matrix

    @classmethod
    def transform_pos_to_index(cls, pos):
        return pos[0] * cls.SCREEN_WIDTH + pos[1]

    @classmethod
    def get_entity_pos(cls, state):
        return [*state][0][1]

    @classmethod
    def get_entity_idx(cls, state):
        pos = cls.get_entity_pos(state)
        idx = cls.transform_pos_to_index(pos)
        return idx
