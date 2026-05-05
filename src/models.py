class Node:
    def __init__(self, id, x, y, demand=0, ready=0, due=1000, service=0, n_type="customer", price=0):
        self.id = id
        self.x = float(x)
        self.y = float(y)
        self.demand = float(demand)
        self.ready_time = float(ready)  # 分钟
        self.due_time = float(due)  # 分钟
        self.service_time = float(service)
        self.type = n_type  # 'depot', 'customer', 'station_private', 'station_public'
        self.price = price  # 充电价格

    def __repr__(self):
        return f"Node({self.id}, {self.type})"

    def to_dict(self):
        """用于序列化保存到 JSON"""
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y
        }