class Node:
    def __init__(self, value = None):
        self.value = value
        self.parent = None
        self.son = None

class Deque:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size: int = 0

    def is_empty(self):
        return self.size == 0

    def add_left(self, value):
        new_head_node = Node(value)

        if self.is_empty():
            self.head = new_head_node
            self.tail = new_head_node
        else:
            new_head_node.son = self.head
            self.head.parent = new_head_node
            self.head = new_head_node

        self.size +=1


    def add_right(self, value):
        new_tail_node = Node(value)

        if self.is_empty():
            self.head = new_tail_node
            self.tail = new_tail_node
        else:
            new_tail_node.parent = self.tail
            self.tail.son = new_tail_node
            self.tail = new_tail_node

        self.size +=1


    def pop_left(self):
        if self.is_empty():
            raise Exception('Дек пуст!')

        value = self.head.value
        self.head = self.head.son

        if self.head:
            self.head.parent = None
        else:
            self.tail = None

        self.size -= 1
        return value


    def pop_right(self):
        if self.is_empty():
            raise Exception('Дек пуст!')

        value = self.tail.value
        self.tail = self.tail.parent

        if self.tail:
            self.tail.son = None
        else:
            self.head = None

        self.size -= 1
        return value

    def __len__(self):
        return self.size

    def __iter__(self):
        current = self.head
        while current:
            yield current.value
            current = current.son