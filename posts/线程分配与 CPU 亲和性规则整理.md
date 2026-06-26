本文整理自酷安 @Aloazny 的三篇线程优化文章，并按“线程分配 / CPU 亲和性 / 子进程分配”的思路重新组织。

原文链接：

- [线程优化简单规则编写](https://www.coolapk.com/feed/64926570?s=Mjk2MjJjN2MxYmMyZTBlZzZhM2U4YjQxegi1631)
- [线程规则简单编写（二）](https://www.coolapk.com/feed/65428151?s=ZGUzY2RmY2IxYmMyZTBlZzZhM2U4YmNjegi1631)
- [子进程分配](https://www.coolapk.com/feed/65446355?s=ZDdjYmNjZjQxYmMyZTBlZzZhM2U4YjJkegi1631)

这篇文章讨论的是：当一个应用里有多个线程、多个子进程时，应该如何把它们限制到合适的 CPU 核心范围里，让高负载线程优先获得性能核心，低负载线程不要抢占关键资源。

## 先理解线程分配

线程分配本质上是在设置 CPU 亲和性，也就是告诉系统：某个进程或线程允许在哪些 CPU 核心上运行。

例如：

```text
example.app.com{RenderThread}=7
example.app.com{main}=4-6
example.app.com=0-5
```

可以理解为：

- `example.app.com{RenderThread}=7`：把 `RenderThread` 限制到 CPU7。
- `example.app.com{main}=4-6`：让 `main` 线程在 CPU4、CPU5、CPU6 之间调度。
- `example.app.com=0-5`：把整个进程限制到 CPU0 到 CPU5。

这里的数字不是固定标准，要看具体 SoC 的核心排列。以常见的 8 核大小核为例，可能是：

| 核心范围 | 常见含义 |
| --- | --- |
| `0-3` | 小核，适合后台、推送、低负载任务 |
| `4-6` | 大核，适合中高负载任务 |
| `7` | 超大核，适合最高负载、最影响流畅度的关键线程 |

不同处理器的核心结构不一样，写规则之前应该先查清楚自己的 CPU 核心架构。

## 一个核心不是同时跑多个线程

一个 CPU 核心在同一时刻只能真正执行一个线程。把一个线程写成 `4-7`，并不代表 CPU4、CPU5、CPU6、CPU7 会同时处理这个线程。

更准确的理解是：这个线程可以在 CPU4 到 CPU7 之间被调度。系统会根据空闲情况、负载、调度策略，把它放到其中一个核心上运行。

例如：

```text
com.example.app{RenderThread}=4-7
```

这表示 `RenderThread` 可以在 `4-7` 之间迁移。如果 CPU6 空闲，它可能跑在 CPU6；如果 CPU6 负载高，系统可能把它迁到 CPU7。

如果某个线程一直是最高负载，直接给它指定性能最强的核心，往往比给一大段核心范围更干净：

```text
com.example.app{RenderThread}=7
```

这样可以减少来回迁移，也更容易让关键线程稳定吃到性能。

## 规则匹配：Fnmatch

很多线程规则会使用类似 shell 的通配符匹配，也就是 Fnmatch。它不是完整正则，但足够匹配常见线程名。

常用写法如下：

| 写法 | 含义 | 示例 |
| --- | --- | --- |
| `*` | 匹配任意数量字符 | `Thread-*` |
| `?` | 匹配单个字符 | `Thread-?` |
| `[0-9]` | 匹配指定范围 | `Thread-[0-9]` |
| `[!2-9]` 或 `[^2-9]` | 排除指定范围 | `Thread-[^2-9]` |

示例：

```text
example.app.com{Thread-*}=4-6
```

它可以匹配：

```text
example.app.com{Thread-1}
example.app.com{Thread-23}
example.app.com{Thread-render}
```

如果只想匹配一个字符：

```text
example.app.com{Thread-?}=4-6
```

它可以匹配 `Thread-1`，但不会匹配 `Thread-12`。

如果想排除某些编号：

```text
example.app.com{Thread-[^1-2]}=4-5
```

这表示匹配 `Thread-1`、`Thread-2` 之外的单字符线程名。

## 按负载分配，而不是按名字感觉分配

线程分配的核心原则是：先观察负载，再决定核心。

一个简单思路：

| 线程负载 | 推荐核心范围 | 说明 |
| --- | --- | --- |
| 最高负载，影响流畅度 | 超大核或最强大核 | 尽量独占，不要被杂线程打扰 |
| 中高负载 | 大核或大核簇 | 看是否需要单独核心 |
| 低负载、后台任务 | 小核或小核簇 | 不要占用性能核心 |
| 瞬时高、平均低 | 大核簇 | 给突发性能，但不抢超大核 |

假设一个处理器里 `7` 是超大核，`4-6` 是大核，`0-3` 是小核。

如果线程负载是：

```text
Thread-1: 30%
Thread-2: 15%
Thread-3: 8%
```

可以写成：

```text
example.app.com{Thread-1}=7
example.app.com{Thread-[2-3]}=4-6
```

如果变成：

```text
Thread-1: 30%
Thread-2: 28%
Thread-3: 15%
```

说明前两个线程都比较重，就可以拆得更细：

```text
example.app.com{Thread-1}=7
example.app.com{Thread-2}=6
example.app.com{Thread-[^1-2]}=4-5
```

这样做的目的不是把核心写得越满越好，而是避免高负载线程互相打扰。

## 一个核心能不能处理多个线程

可以，但要看负载。

如果两个线程都不重，同一个大核或超大核可以轮流处理它们。只要单核没有长期接近满载，就不一定会卡。

例如日用场景里：

```text
com.example.app{RenderThread}=7
com.example.app{main}=7
```

如果 `RenderThread` 和 `main` 的负载都不高，超大核可以顺序或乱序处理它们。甚至在线程空闲时，还能处理其他任务。

但这个思路更适合日常应用。游戏里关键线程负载往往很高，把多个重线程塞到同一个核心，容易造成帧时间抖动。

## 日常应用怎么分

日常应用通常更看重启动速度、滑动流畅度和页面响应。

冷启动时，应用可能会同时做这些事：

- 读取文件和数据库。
- 初始化框架。
- 优化或加载 Dex。
- 创建 UI。
- 做网络和缓存初始化。

这类阶段比较吃多核心协同，可以给进程或主线程一个相对宽的性能核心范围。

示例：

```text
com.example.pay=4-7
com.example.pay{main}=4-7
```

运行中则更看重单核性能。哪个线程负载高、最影响滑动和渲染，就优先给性能核心。

如果只是轻量支付、扫码、消息列表这类日用场景，不一定需要非常激进地独占超大核。大核簇通常已经够用：

```text
com.example.app{main}=4-6
com.example.app{RenderThread}=4-6
```

## 游戏怎么分

游戏场景和日常应用不一样。游戏里经常有一个或两个特别关键的高负载线程，例如主逻辑线程、渲染线程、图形设备线程。

这里要关注两个指标：

- `AVG`：平均负载。
- `MAX`：瞬时最高负载。

如果某个线程平均负载高，瞬时负载也高，它就应该优先放到最强核心，并尽量不要让其他线程抢这个核心。

例如：

```text
com.game.example{UnityMain}=7
```

如果另一个图形线程负载中高，可以给单独大核：

```text
com.game.example{UnityGfxDeviceW}=6
```

也可以给大核簇：

```text
com.game.example{UnityGfxDeviceW}=4-6
```

但如果 `UnityMain` 已经占用超大核，就不建议把其他中高负载线程也写到 `7`：

```text
com.game.example{UnityGfxDeviceW}=4-7
com.game.example{UnityGfxDeviceW}=7
```

这种写法可能导致关键线程和图形线程轮流争抢超大核，帧时间更容易抖。

更稳的写法是：

```text
com.game.example{UnityMain}=7
com.game.example{UnityGfxDeviceW}=6
com.game.example{Thread-*}=4-6
com.game.example{Loading*}=4-6
com.game.example{Job.Worker*}=4-5
com.game.example=0-5
```

这里的思路是：

- `UnityMain` 独占超大核。
- 图形线程走大核。
- worker、loading 这类瞬时任务走大核簇。
- 进程兜底限制到 `0-5`，避免杂线程影响 `7`。

## 子进程怎么分

很多 Android 应用不只有主进程，还会有子进程。浏览器、小程序、WebView、GPU 渲染、下载、推送服务都可能拆成单独进程。

常见子进程名称大概长这样：

```text
io.github.example.browser
io.github.example.browser:tab15
io.github.example.browser:gpu
io.github.example.browser:crashhelper
```

带 `:` 的通常就是子进程。

对于浏览器类应用，网页内容进程可能才是真正高负载的地方。例如 `:tab*` 这类进程可能承载 Web Content：

```text
io.github.example.browser:tab*=4-7
```

对于 GPU、渲染、小程序相关子进程，可以给大核或性能核心：

```text
com.example.app:gpu_process=4-6
com.example.app:renderer_process0=4-7
com.example.app:appbrand0=4-7
```

对于下载、媒体播放这类服务，可以看实际需求给大核、小核或混合核心：

```text
com.example.app:DownloadService=0-5
com.example.app:MediaPlayerService=0-6
```

对于推送、保活、小组件这类轻量服务，一般放小核即可：

```text
com.example.app:push=0-1
com.example.app:xg_vip_service=0-3
```

也有例外。比如某些模拟器或容器类应用，真正运行游戏的可能是子进程，主进程反而退到后台。这种情况就要按子进程里的线程负载重新细分，不能只看主进程。

## 如何查看子进程

可以用进程管理工具查看，也可以用终端。

终端里常见方式：

```sh
su
pgrep -lf 应用包名
```

例如：

```sh
pgrep -lf io.github.example.browser
```

输出里如果看到 `包名:xxx`，一般就是子进程。复制完整命令行后，再按实际进程名写规则。

## 常见错误

### 误区一：以为一个线程能被多个核心同时执行

写成：

```text
com.example.app{RenderThread}=4-7
```

不代表四个核心一起跑 `RenderThread`。它只是允许这个线程在 `4-7` 范围内被调度。

### 误区二：所有线程都给超大核

超大核很强，但不是垃圾桶。关键线程需要它，杂线程也抢它，最后可能更卡。

### 误区三：只看线程名，不看负载

线程名只能帮助定位，真正决定分配策略的是负载。尤其游戏线程，要看平均负载和瞬时最高负载。

### 误区四：把游戏关键线程写得太宽

关键线程如果在多个核心间迁移，可能带来缓存和调度抖动。高负载主线程通常更适合固定到最强核心。

### 误区五：忽略子进程

很多应用的高负载不在主进程，而在 `:gpu`、`:renderer`、`:tab*`、`:appbrand` 这类子进程里。只写主进程规则，可能没有优化到真正的热点。

## 推荐流程

比较稳的线程分配流程是：

1. 先确认 CPU 核心架构，弄清楚小核、大核、超大核编号。
2. 打开目标应用，复现真实使用场景。
3. 观察线程或子进程负载，区分平均负载和瞬时负载。
4. 找到最高负载、最影响体验的关键线程。
5. 给关键线程分配最强核心，避免其他线程抢占。
6. 把中等负载线程分给大核簇。
7. 把低负载、后台、推送类任务分给小核。
8. 重新测试流畅度、功耗、温度和卡顿情况。

不要一上来就套别人完整规则。不同处理器核心结构不同，不同应用线程命名不同，同一个应用不同版本的线程负载也可能变化。

## 小结

线程分配的重点不是“把所有东西都丢到大核”，而是把最需要性能的线程放到最合适的核心上。

日常应用可以适当给宽一点的性能核心范围，让启动和滑动更顺。游戏则要更谨慎，最高负载线程最好独占最强核心，其他中低负载线程分流到大核或小核。遇到浏览器、小程序、WebView、模拟器这类应用，还要额外关注子进程。

一句话总结：先观察负载，再写规则；先保护关键线程，再安排其他线程。
