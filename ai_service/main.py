from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

# 1. Định nghĩa State của Graph
class State(TypedDict):
    approved: bool
    status: str

# 2. Định nghĩa node có chứa interrupt
def approval_node(state: State):
    print("\n[Node] Đang chạy approval_node...")
    
    # Hàm interrupt sẽ TẠM DỪNG execution ở đây.
    # Giá trị truyền vào interrupt() sẽ được trả ra bên ngoài làm thông báo.
    approved = interrupt("Do you approve this action?")

    # Khi người dùng RESUME (tiếp tục), giá trị được gửi từ lệnh resume 
    # sẽ được gán vào biến `approved` này.
    print(f"[Node] Đã nhận được phản hồi: {approved}")
    
    return {
        "approved": approved,
        "status": "Hoàn tất xử lý sau duyệt" if approved else "Đã từ chối"
    }

# 3. Dựng Graph
builder = StateGraph(State)
builder.add_node("approval_node", approval_node)

builder.add_edge(START, "approval_node")
builder.add_edge("approval_node", END)

# BẮT BUỘC phải dùng checkpointer (MemorySaver) để lưu state khi bị interrupt
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# -------------------------------------------------------------
# CHẠY THỬ
# -------------------------------------------------------------

# Thread ID giúp LangGraph biết đang tạm dừng ở luồng (phiên) nào
config = {"configurable": {"thread_id": "session_1"}}

print("=== BƯỚC 1: Chạy luồng đến khi gặp interrupt ===")
# Lần đầu kích hoạt graph với state ban đầu
for chunk in graph.stream({"approved": False, "status": "Chưa duyệt"}, config):
    print("Chunk:", chunk)

# Kiểm tra trạng thái hiện tại của Graph
state_snapshot = graph.get_state(config)
print("\n--> Graph hiện tại đã dừng!")
print("Next node cần chạy:", state_snapshot.next)
print("Thông điệp từ Interrupt:", state_snapshot.tasks[0].interrupts[0].value if state_snapshot.tasks else "None")

input("\n[Nhấn Enter để tiếp tục gửi lệnh Resume...]")

print("\n=== BƯỚC 2: Resume luồng làm việc và gửi giá trị đồng ý (True) ===")
# Dùng Command(resume=...) để truyền giá trị quay lại biến `approved` trong node
for chunk in graph.stream(Command(resume=True), config):
    print("Chunk:", chunk)

# Kiểm tra kết quả cuối cùng
final_state = graph.get_state(config)
print("\n=== KẾT QUẢ CUỐI CÙNG ===")
print("State trong bộ nhớ:", final_state.values)