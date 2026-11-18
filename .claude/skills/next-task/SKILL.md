---
name: next-task
description: Làm task tiếp theo (hoặc task ID được chỉ định) của BTL theo PLAN.md, kèm test, module .md và cập nhật PROGRESS.md.
argument-hint: "[task-id, vd. P3.1 — bỏ trống = task tiếp theo]"
disable-model-invocation: true
---

Task được yêu cầu: $ARGUMENTS (trống → chọn task như mô tả đầu `docs/WORKFLOW.md` §1).

Làm theo `docs/WORKFLOW.md` mục 1 "Làm task", đúng thứ tự, không bỏ bước. Ở bước 7 (tự kiểm) gọi subagent `spec-reviewer` với task ID.
