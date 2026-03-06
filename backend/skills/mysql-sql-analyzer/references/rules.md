# MySQL 执行计划判读规则

## 表访问级别（access_type）

- `const` / `eq_ref` / `ref` / `range`：通常优于全表扫描。
- `index`：扫描索引全量，可能仍然很重。
- `ALL`：全表扫描，高优先级关注。

## 风险规则

1. `full_table_scan`
- 条件：`access_type=ALL`
- 含义：未有效利用索引，扫描成本高。

2. `index_not_chosen`
- 条件：`possible_keys` 非空但 `key` 为空
- 含义：有候选索引但优化器未选择，可能因为选择性不足、类型转换、函数包裹等。

3. `using_filesort`
- 条件：执行计划包含 `using_filesort=true`
- 含义：排序无法通过索引完成，可能触发额外排序开销。

4. `using_temporary_table`
- 条件：执行计划包含 `using_temporary_table=true`
- 含义：分组/排序过程需要临时表，内存或磁盘代价升高。

5. `low_filtered_ratio`
- 条件：`rows_examined_per_scan > 1000` 且 `filtered < 20`
- 含义：读取大量记录后才过滤，谓词选择性弱。

## 优化优先级建议

1. 先解决 `ALL` 与未命中索引问题（索引设计、谓词改写）。
2. 再解决 `filesort/temporary`（匹配排序与分组顺序的联合索引）。
3. 最后用 `EXPLAIN ANALYZE` 验证真实执行时间与行数偏差。
