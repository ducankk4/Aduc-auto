# Chính sách đặt cọc, hủy đơn và hoàn tiền

> Nội dung nháp do AI soạn để có corpus test pipeline ingest — đội ngũ nghiệp vụ
> cần rà soát và thay bằng chính sách thật trước khi dùng cho khách hàng thật.
> Không có số tiền cụ thể nào trong file này — tiền cọc luôn phải lấy từ API
> backend tại thời điểm trả lời, không lấy từ nội dung tư vấn tĩnh này.

## Đặt cọc

Khi khách hàng xác nhận đặt cọc cho một cấu hình xe (phiên bản + màu sắc) cụ
thể, hệ thống sẽ tạo một đơn hàng ở trạng thái chờ thanh toán. Số tiền cọc phụ
thuộc vào phiên bản và màu xe đã chọn, luôn được backend tính toán tại thời
điểm tạo đơn — không có một mức cọc cố định áp dụng chung cho mọi xe.

Sau khi đặt cọc thành công, khoản tiền này được xem là một phần của tổng giá
trị xe, sẽ được khấu trừ vào số tiền còn lại khi khách hàng hoàn tất thanh
toán và nhận xe tại showroom.

## Hủy đơn

Khách hàng có quyền yêu cầu hủy đơn đặt cọc trong thời gian đơn còn ở trạng
thái chờ thanh toán hoặc đã thanh toán nhưng chưa được showroom xác nhận giao
xe. Sau khi đơn đã được xác nhận (trạng thái "confirmed"), việc hủy đơn cần
liên hệ trực tiếp showroom phụ trách để xử lý theo từng trường hợp cụ thể.

Yêu cầu hủy đơn được ghi nhận qua hệ thống và xử lý bởi nhân viên phụ trách,
không phải là một hành động agent AI có thể tự thực hiện thay khách hàng mà
không qua xác nhận rõ ràng.

## Hoàn tiền

Khi đơn được hủy hợp lệ, tiền cọc sẽ được hoàn lại theo phương thức thanh toán
ban đầu. Thời gian xử lý hoàn tiền thường mất một khoảng thời gian xử lý ngân
hàng/cổng thanh toán trước khi tiền về tài khoản khách hàng — thời gian cụ thể
phụ thuộc vào ngân hàng phát hành và cổng thanh toán được sử dụng.

Nếu đơn đã chuyển sang trạng thái "refunded", nghĩa là quá trình hoàn tiền đã
được ghi nhận hoàn tất trong hệ thống.

## Lưu ý khi tư vấn

- Không tự suy đoán số tiền cọc hay thời gian xử lý cụ thể bằng số — nếu khách
  hỏi con số chính xác, luôn tra cứu qua tool tương ứng hoặc đề nghị khách chờ
  nhân viên xác nhận.
- Nếu khách hỏi về trường hợp đặc biệt không nằm trong nội dung này, trả lời
  trung thực là cần liên hệ showroom/nhân viên phụ trách để được hỗ trợ.
