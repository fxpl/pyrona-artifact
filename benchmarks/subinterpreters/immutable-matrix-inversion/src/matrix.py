import random


class Matrix:
    def __init__(self):
        self.values = [0.0, 0.0, 0.0, 0.0,
                       0.0, 0.0, 0.0, 0.0,
                       0.0, 0.0, 0.0, 0.0,
                       0.0, 0.0, 0.0, 0.0]

    def invert(self, inverse: "Matrix") -> bool:
        m = self.values
        inv = inverse.values
        inv[0] = (m[5] * m[10] * m[15] -
                  m[5] * m[11] * m[14] -
                  m[9] * m[6] * m[15] +
                  m[9] * m[7] * m[14] +
                  m[13] * m[6] * m[11] -
                  m[13] * m[7] * m[10])

        inv[4] = (-m[4] * m[10] * m[15] +
                  m[4] * m[11] * m[14] +
                  m[8] * m[6] * m[15] -
                  m[8] * m[7] * m[14] -
                  m[12] * m[6] * m[11] +
                  m[12] * m[7] * m[10])

        inv[8] = (m[4] * m[9] * m[15] -
                  m[4] * m[11] * m[13] -
                  m[8] * m[5] * m[15] +
                  m[8] * m[7] * m[13] +
                  m[12] * m[5] * m[11] -
                  m[12] * m[7] * m[9])

        inv[12] = (-m[4] * m[9] * m[14] +
                   m[4] * m[10] * m[13] +
                   m[8] * m[5] * m[14] -
                   m[8] * m[6] * m[13] -
                   m[12] * m[5] * m[10] +
                   m[12] * m[6] * m[9])

        inv[1] = (-m[1] * m[10] * m[15] +
                  m[1] * m[11] * m[14] +
                  m[9] * m[2] * m[15] -
                  m[9] * m[3] * m[14] -
                  m[13] * m[2] * m[11] +
                  m[13] * m[3] * m[10])

        inv[5] = (m[0] * m[10] * m[15] -
                  m[0] * m[11] * m[14] -
                  m[8] * m[2] * m[15] +
                  m[8] * m[3] * m[14] +
                  m[12] * m[2] * m[11] -
                  m[12] * m[3] * m[10])

        inv[9] = (-m[0] * m[9] * m[15] +
                  m[0] * m[11] * m[13] +
                  m[8] * m[1] * m[15] -
                  m[8] * m[3] * m[13] -
                  m[12] * m[1] * m[11] +
                  m[12] * m[3] * m[9])

        inv[13] = (m[0] * m[9] * m[14] -
                   m[0] * m[10] * m[13] -
                   m[8] * m[1] * m[14] +
                   m[8] * m[2] * m[13] +
                   m[12] * m[1] * m[10] -
                   m[12] * m[2] * m[9])

        inv[2] = (m[1] * m[6] * m[15] -
                  m[1] * m[7] * m[14] -
                  m[5] * m[2] * m[15] +
                  m[5] * m[3] * m[14] +
                  m[13] * m[2] * m[7] -
                  m[13] * m[3] * m[6])

        inv[6] = (-m[0] * m[6] * m[15] +
                  m[0] * m[7] * m[14] +
                  m[4] * m[2] * m[15] -
                  m[4] * m[3] * m[14] -
                  m[12] * m[2] * m[7] +
                  m[12] * m[3] * m[6])

        inv[10] = (m[0] * m[5] * m[15] -
                   m[0] * m[7] * m[13] -
                   m[4] * m[1] * m[15] +
                   m[4] * m[3] * m[13] +
                   m[12] * m[1] * m[7] -
                   m[12] * m[3] * m[5])

        inv[14] = (-m[0] * m[5] * m[14] +
                   m[0] * m[6] * m[13] +
                   m[4] * m[1] * m[14] -
                   m[4] * m[2] * m[13] -
                   m[12] * m[1] * m[6] +
                   m[12] * m[2] * m[5])

        inv[3] = (-m[1] * m[6] * m[11] +
                  m[1] * m[7] * m[10] +
                  m[5] * m[2] * m[11] -
                  m[5] * m[3] * m[10] -
                  m[9] * m[2] * m[7] +
                  m[9] * m[3] * m[6])

        inv[7] = (m[0] * m[6] * m[11] -
                  m[0] * m[7] * m[10] -
                  m[4] * m[2] * m[11] +
                  m[4] * m[3] * m[10] +
                  m[8] * m[2] * m[7] -
                  m[8] * m[3] * m[6])

        inv[11] = (-m[0] * m[5] * m[11] +
                   m[0] * m[7] * m[9] +
                   m[4] * m[1] * m[11] -
                   m[4] * m[3] * m[9] -
                   m[8] * m[1] * m[7] +
                   m[8] * m[3] * m[5])

        inv[15] = (m[0] * m[5] * m[10] -
                   m[0] * m[6] * m[9] -
                   m[4] * m[1] * m[10] +
                   m[4] * m[2] * m[9] +
                   m[8] * m[1] * m[6] -
                   m[8] * m[2] * m[5])

        det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]

        if det == 0:
            return False

        det = 1.0 / det

        for i in range(16):
            inv[i] = inv[i] * det

        i00 = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
        i01 = m[0] * inv[1] + m[1] * inv[5] + m[2] * inv[9] + m[3] * inv[13]
        i02 = m[0] * inv[2] + m[1] * inv[6] + m[2] * inv[10] + m[3] * inv[14]
        i03 = m[0] * inv[3] + m[1] * inv[7] + m[2] * inv[11] + m[3] * inv[15]
        i10 = m[4] * inv[0] + m[5] * inv[4] + m[6] * inv[8] + m[7] * inv[12]
        i11 = m[4] * inv[1] + m[5] * inv[5] + m[6] * inv[9] + m[7] * inv[13]
        i12 = m[4] * inv[2] + m[5] * inv[6] + m[6] * inv[10] + m[7] * inv[14]
        i13 = m[4] * inv[3] + m[5] * inv[7] + m[6] * inv[11] + m[7] * inv[15]
        i20 = m[8] * inv[0] + m[9] * inv[4] + m[10] * inv[8] + m[11] * inv[12]
        i21 = m[8] * inv[1] + m[9] * inv[5] + m[10] * inv[9] + m[11] * inv[13]
        i22 = m[8] * inv[2] + m[9] * inv[6] + m[10] * inv[10] + m[11] * inv[14]
        i23 = m[8] * inv[3] + m[9] * inv[7] + m[10] * inv[11] + m[11] * inv[15]
        i30 = m[12] * inv[0] + m[13] * inv[4] + m[14] * inv[8] + m[15] * inv[12]
        i31 = m[12] * inv[1] + m[13] * inv[5] + m[14] * inv[9] + m[15] * inv[13]
        i32 = m[12] * inv[2] + m[13] * inv[6] + m[14] * inv[10] + m[15] * inv[14]
        i33 = m[12] * inv[3] + m[13] * inv[7] + m[14] * inv[11] + m[15] * inv[15]

        diagonal = i00 + i11 + i22 + i33
        off_diagonal = i01 + i02 + i03 + i10 + i12 + i13 + i20 + i21 + i23 + i30 + i31 + i32
        if abs(diagonal - 4) > 1e-3 or abs(off_diagonal) > 1e-3:
            print(diagonal, off_diagonal)
            return False

        return True


def random_matrix(min_value: float, max_value: float) -> Matrix:
    scale = max_value - min_value
    m = Matrix()
    m.values = [random.random() * scale + min_value for _ in range(16)]
    return m
