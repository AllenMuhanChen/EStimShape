class newFloat(float):
    def __init__(self, value, index):
        super().__init__(value)
        self.index = index

    def __new__(cls, value, index):
        return super().__new__(cls, value)

new = newFloat(5.0, 5)