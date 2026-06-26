本文整理自酷安 @海边会下雪么 的 SQLite 数据库优化相关内容，并结合 SQLite 官方文档补充 `VACUUM`、`auto_vacuum`、WAL 与维护策略。

(本文为叹雪整理版，非逐字转载，原文请看[酷安原文](https://www.coolapk.com/feed/71050975?s=N2VmODY2NTgxYmMyZTBlZzZhM2U3NGRiegi1631))

SQLite 是 Android 和很多轻量应用里常见的本地数据库。它把表、索引、元信息都放在一个数据库文件里，读写简单，部署方便，但长期插入、更新、删除后，文件内部可能出现空洞和碎片。`VACUUM` 的作用就是重建数据库文件，让有效数据重新紧凑排列，并把可释放的空闲页归还给文件系统。

## 这是什么技术

`VACUUM` 是 SQLite 提供的数据库整理命令。它不是清缓存，也不是删除业务数据，而是对数据库文件本身做一次重写整理。

它主要解决三个问题：

- 删除大量数据后，数据库文件没有明显变小。
- 表和索引的数据页分布零散，文件内部碎片变多。
- 部分页只填了一点数据，整体空间利用率下降。

可以把 SQLite 数据库理解成一组固定大小的页面。删除数据时，很多页面会被标记为空闲页，但这些空间通常仍留在数据库文件内部。`VACUUM` 会把仍然有效的数据复制到一个新的紧凑文件里，再用新文件替换旧文件。

![SQLite 数据库碎片化与整理前后对比](posts/assets/sqlite-vacuum-fragmentation.svg)

## 碎片为什么会出现

SQLite 使用页来管理数据库文件，常见页大小是 4096 字节，但实际取决于数据库创建时的配置。表和索引的数据会被组织在 B-tree 结构中，增删改操作会不断改变这些页的占用状态。

当应用频繁删除数据时，被删除记录占用的空间会变成可复用空间。SQLite 以后插入新数据时可以继续使用它们，但如果后续数据量没有恢复到原来的规模，文件体积就不会自动缩回去。

当应用频繁更新变长字段、批量插入再批量删除、反复维护索引时，数据页还可能变得分散。对于读取来说，碎片化不一定每次都会造成明显卡顿，但会提高文件占用，也可能让扫描、索引访问和备份成本变高。

## VACUUM 的实现原理

SQLite 官方文档对 `VACUUM` 的描述很直接：它会重建数据库文件，并把数据库重新打包到尽可能少的磁盘空间中。

内部过程可以按下面理解：

1. SQLite 创建一个临时数据库文件。
2. 按表、索引等结构读取旧数据库里的有效内容。
3. 把有效内容写入临时数据库，让页面重新紧凑排列。
4. 复制完成后，用整理后的文件替换原数据库。
5. 原来散落的空闲页、部分填充页和碎片空间被清理掉。

![SQLite VACUUM 重建数据库文件流程](posts/assets/sqlite-vacuum-flow.svg)

这个过程本质上是重写数据库，所以它比普通 `DELETE` 或 `UPDATE` 更重。数据库越大，I/O 成本越高，临时空间需求也越高。

## 整理前如何判断是否值得执行

不建议只要看到 SQLite 数据库就执行 `VACUUM`。更合理的做法是先看数据库内部到底有没有足够多的可回收空间。

可以用这几个 `PRAGMA` 做估算：

```sql
PRAGMA page_size;
PRAGMA page_count;
PRAGMA freelist_count;
```

含义如下：

- `page_size`：每个数据库页的大小。
- `page_count`：当前数据库总页数。
- `freelist_count`：当前空闲页数量，也就是可复用但还没有归还给文件系统的页面。

一个简单估算公式：

```text
可回收空间约等于 freelist_count * page_size
空闲页比例约等于 freelist_count / page_count
```

如果 `freelist_count` 很小，执行 `VACUUM` 的收益就有限。如果刚删除了大量聊天记录、日志、缓存索引或历史数据，`freelist_count` 明显上升，这时整理更有意义。

## 执行时机

`VACUUM` 需要对数据库做独占整理，不适合在业务高峰期执行。对于移动端应用，比较适合的时机通常是：

- 应用冷启动后的低负载阶段。
- 用户退出主要页面之后。
- 充电、息屏、空闲等维护窗口。
- 批量删除数据之后，但要避开立刻读写数据库的阶段。

对于后台服务，可以放在低峰时间，并加上执行频率限制。每天、每周或按阈值触发都可以，关键是不要无脑高频执行。

![SQLite 数据库整理执行策略](posts/assets/sqlite-vacuum-strategy.svg)

## WAL 模式下要注意什么

很多 SQLite 数据库会使用 WAL，也就是 write-ahead logging。WAL 模式下，新写入内容会先进入 `-wal` 文件，之后再通过 checkpoint 合并回主数据库文件。

这会带来两个容易误判的地方：

- 只看主 `.db` 文件大小不够，`-wal` 文件也可能占用大量空间。
- 执行整理前后，如果没有处理 checkpoint，文件大小变化可能不符合预期。

常见维护顺序可以是：

```sql
PRAGMA wal_checkpoint(TRUNCATE);
VACUUM;
```

`wal_checkpoint(TRUNCATE)` 会尝试把 WAL 内容写回主库，并截断 WAL 文件。之后再执行 `VACUUM`，更容易观察主数据库文件的真实整理效果。

如果只是想修改 `page_size`，需要特别注意：SQLite 官方文档说明，进入 WAL 模式后不能通过 `VACUUM` 改变页面大小。要修改页面大小，需要切回 rollback journal 模式后再处理。

## auto_vacuum 和 VACUUM 的区别

SQLite 还有一个容易混淆的配置叫 `auto_vacuum`。

`VACUUM` 是一次完整重建数据库文件。它会整理页面布局，并回收空闲页。

`auto_vacuum=FULL` 会在提交事务时把空闲页移动到文件末尾并截断文件，所以文件可能更及时变小。但它并不会像完整 `VACUUM` 那样重新整理所有表和索引的布局，频繁移动页面还可能增加碎片。

`auto_vacuum=INCREMENTAL` 则需要配合：

```sql
PRAGMA incremental_vacuum;
```

它适合想分批回收空间的场景，但前提是数据库启用了增量回收所需的指针信息。一般来说，`auto_vacuum` 最好在数据库创建早期就规划好。已有数据库想切换相关模式，通常需要设置 PRAGMA 后再执行一次 `VACUUM`。

## 常见限制和风险

`VACUUM` 很有用，但它不是无成本操作。

需要注意这些限制：

- 不能在事务内部执行。
- 需要没有其他连接正在持有会冲突的读写操作。
- 执行期间会产生大量 I/O，数据库越大越明显。
- 通常需要额外临时磁盘空间，最坏情况下要接近原数据库大小。
- 没有显式 `INTEGER PRIMARY KEY` 的表，执行后内部 `ROWID` 可能变化。
- 如果设备突然断电或空间不足，虽然 SQLite 会尽量保证一致性，但维护任务仍应避开风险时段。

所以，`VACUUM` 更像数据库维护动作，不应该当成普通查询频繁调用。

## 一个比较稳的维护流程

可以按下面流程做：

```sql
PRAGMA page_size;
PRAGMA page_count;
PRAGMA freelist_count;

PRAGMA wal_checkpoint(TRUNCATE);
VACUUM;

PRAGMA freelist_count;
PRAGMA page_count;
```

执行前先记录 `page_count` 和 `freelist_count`，执行后再看变化。如果空闲页归零或明显减少，文件大小也下降，就说明整理确实起效。

如果数据库较大，建议再加几个工程保护：

- 先确认剩余磁盘空间足够。
- 避开用户正在操作数据库的时间段。
- 给执行过程加超时和失败记录。
- 维护失败时不要反复立即重试。
- 对关键数据库先做好备份策略。

## Android 场景里的思路

Android 应用经常把配置、聊天、日志、索引、缓存元信息写进 SQLite。长期使用后，用户删除了大量数据，但 `.db` 文件仍然很大，这是很典型的可整理场景。

如果应用自己控制数据库连接，可以在合适时机执行：

```sql
VACUUM;
```

如果使用框架封装数据库，也要确保执行时没有外层事务，没有其他线程正在大量读写同一个库。对用户体验来说，宁可少执行，也不要在前台交互时突然触发重 I/O。

## 小结

`VACUUM` 的核心价值是重建 SQLite 数据库文件，回收空闲页，降低文件膨胀，并让表和索引数据更紧凑。它适合数据库经历大量删除或长期碎片积累后的维护，不适合高频、无判断地运行。

比较推荐的策略是：先用 `freelist_count` 判断是否值得整理，再在低负载窗口执行，并在 WAL 模式下配合 checkpoint。这样既能减少无效 I/O，也能让数据库维护更可控。

## 参考资料

- [SQLite VACUUM 官方文档](https://www.sqlite.org/lang_vacuum.html)
- [SQLite PRAGMA 官方文档](https://www.sqlite.org/pragma.html)
- [SQLite Write-Ahead Logging 官方文档](https://www.sqlite.org/wal.html)
