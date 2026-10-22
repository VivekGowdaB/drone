import math

class Vec3:
    __slots__ = ['x', 'y', 'z']

    def __init__(self, x=0.0, y=None, z=None):
        if isinstance(x, (list, tuple)) and len(x) == 3:
            self.x, self.y, self.z = map(float, x)
        elif y is None and z is None:
            if hasattr(x, 'x') and hasattr(x, 'y') and hasattr(x, 'z'):
                self.x, self.y, self.z = float(x.x), float(x.y), float(x.z)
            elif isinstance(x, (int, float)):
                self.x = self.y = self.z = float(x)
            else:
                self.x = self.y = self.z = 0.0
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def __add__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return Vec3(self.x + other, self.y + other, self.z + other)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return Vec3(self.x - other, self.y - other, self.z - other)

    def __rsub__(self, other):
        if isinstance(other, Vec3):
            return Vec3(other.x - self.x, other.y - self.y, other.z - self.z)
        return Vec3(other - self.x, other - self.y, other - self.z)

    def __mul__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x / other.x, self.y / other.y, self.z / other.z)
        return Vec3(self.x / other, self.y / other, self.z / other)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __eq__(self, other):
        if isinstance(other, Vec3):
            return self.x == other.x and self.y == other.y and self.z == other.z
        return False

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self):
        l = self.length()
        if l == 0:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / l, self.y / l, self.z / l)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def __repr__(self):
        return f"Vec3({self.x}, {self.y}, {self.z})"


def lerp(a, b, t):
    """Linear interpolation between a and b."""
    if isinstance(a, Vec3) and isinstance(b, Vec3):
        return a + (b - a) * t
    return a + (b - a) * t
