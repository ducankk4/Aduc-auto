# Hướng dẫn đăng ký lái thử

> Nội dung nháp do AI soạn để có corpus test pipeline ingest — đội ngũ nghiệp vụ
> cần rà soát và thay bằng nội dung thật trước khi dùng cho khách hàng thật.
> Phạm vi hiện tại của AI là ghi nhận nguyện vọng lái thử dưới dạng thông tin
> liên hệ + showroom mong muốn, KHÔNG đặt lịch theo ngày giờ cụ thể (danh sách
> showroom và lịch làm việc chưa có endpoint công khai).

## Quy trình đăng ký lái thử

1. Khách hàng cho biết xe muốn lái thử (có thể là một hoặc nhiều mẫu xe đang
   quan tâm).
2. Khách hàng cung cấp thông tin liên hệ: họ tên, số điện thoại, email (nếu
   có), và showroom mong muốn (ghi theo nguyện vọng dạng văn bản tự do, ví dụ
   "showroom gần quận 1" hoặc tên showroom cụ thể nếu khách biết).
3. Thông tin được ghi nhận thành một yêu cầu tư vấn/lái thử trong hệ thống.
   Nhân viên showroom phụ trách sẽ chủ động liên hệ lại khách hàng để thống
   nhất thời gian lái thử cụ thể.

## Những điều AI hiện chưa hỗ trợ được

- Không đặt lịch lái thử theo một khung giờ cố định trong hệ thống — việc
  thống nhất thời gian cụ thể do nhân viên showroom liên hệ trực tiếp.
- Không liệt kê danh sách đầy đủ các showroom kèm địa chỉ/giờ mở cửa trong
  hội thoại tự động — nếu khách cần thông tin này ngay, nên đề nghị khách để
  lại thông tin liên hệ để nhân viên tư vấn cụ thể hơn.
- Không xác nhận thay khách việc xe có sẵn để lái thử tại thời điểm khách
  mong muốn — đây là thông tin nhân viên showroom xác nhận trực tiếp.

## Lưu ý khi tư vấn

- Luôn xác nhận lại với khách các thông tin đã thu thập trước khi gửi yêu cầu
  đăng ký (đúng tinh thần "mọi thao tác ghi phải qua xác nhận người dùng").
- Nếu khách hỏi về việc chọn thêm option/trang bị khi lái thử, hiện hệ thống
  chưa hỗ trợ quản lý option xe — không hứa hẹn tính năng này với khách.
