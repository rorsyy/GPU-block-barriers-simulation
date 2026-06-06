# 参考文献汇总表（按正文出现顺序排列）

| 新编号 | 原编号 | 作者 | 标题 | 类型 | 出处/出版信息 | 年份 | 内容概要 | 首次出现位置 |
|--------|--------|------|------|------|-------------|------|---------|-------------|
| [1] | [14] | Brooks A, Marshall P, Ozog D, 等 | Intel SHMEM: GPU-Initiated OpenSHMEM Using SYCL | [EB/OL] | arXiv:2409.20476 | 2024 | 将OpenSHMEM通信机制引入GPU kernel内部，使线程块之间数据交换不依赖复杂全局内存管理，实现GPU侧发起的跨块通信 | §1.1 |
| [2] | [1] | 高岚, 赵雨晨, 张伟功, 等 | 面向GPU并行编程的线程同步综述 | [J] | 软件学报, 35(2): 1028-1047 | 2024 | 对GPU线程同步机制进行系统分类，总结不同同步粒度与实现方式的特点，涵盖CUDA线程束、线程块及跨线程块同步技术 | §1.1 |
| [3] | [3] | Aamodt T M, Fung W W L, Rogers T G | General-Purpose Graphics Processor Architectures | [M] | Cham: Springer Nature Switzerland AG | 2022 | 通用GPU架构专著，系统讲解GPU SIMT执行模型、调度策略、内存层次结构及线程同步的硬件约束与死锁问题 | §1.1 |
| [4] | [4] | Xiao S, Feng W | Inter-Block GPU Communication via Fast Barrier Synchronization | [C] | Proceedings of the 2010 IEEE International Symposium on Parallel and Distributed Processing. Piscataway: IEEE, 2010: 1-12 | 2010 | 提出基于全局内存和原子操作的GPU跨线程块栅栏同步方案，在FFT、动态规划和双调排序中验证GPU侧同步有效性 | §1.1 |
| [5] | [9] | Kirk D B, Hwu W W, Hajj I E | Programming Massively Parallel Processors: A Hands-on Approach | [M] | 4th ed. Cambridge: Morgan Kaufmann | 2022 | CUDA编程经典教材，系统讲解GPU并行编程模型、内存层次、同步原语及原子操作的性能特性 | §1.1 |
| [6] | [2] | NVIDIA | NVIDIA H100 Tensor Core Architecture Overview | [R] | Santa Clara: NVIDIA Corporation | 2022 | NVIDIA H100 GPU架构白皮书，介绍Hopper架构线程块簇（Thread Block Cluster）机制及硬件同步特性 | §1.1 |
| [7] | [5] | Liu J W | Efficient Synchronization for GPGPU | [D] | Pittsburgh: University of Pittsburgh | 2018 | 提出Gsync框架，通过硬件-软件协同方式避免跨线程块同步死锁，减少同步过程的流水线停顿 | §1.1 |
| [8] | [16] | Lubachevsky B D | Synchronization Barrier and Related Tools for Shared Memory Parallel Programming | [J] | International Journal of Parallel Programming, 1990, 19(3): 225-250 | 1990 | 提出基于二叉树归约与广播的高效栅栏结构，系统分析共享内存并行编程中栅栏同步的理论基础与性能模型 | §1.1 |
| [9] | [6] | Ge T, Zhang T, Liu H | ngAP: Non-Blocking Large-Scale Automata Processing on GPUs | [C] | Proceedings of the 29th ACM International Conference on Architectural Support for Programming Languages and Operating Systems. New York: ACM, 2024: 268-285 | 2024 | 提出非阻塞大规模自动机处理的ngAP框架，通过预取、状态复用与线程私有化将串行依赖转化为流水线并行，降低阻塞等待开销 | §1.2 |
| [10] | [8] | Chen H, Fan B, Collins A, 等 | Tawa: Automatic Warp Specialization for Modern GPUs with Asynchronous References | [EB/OL] | arXiv:2510.14719 | 2025 | 提出Tawa编译器，将线程束划分为生产者与消费者，通过环形缓冲区与硬件信号量实现异步流水线执行 | §1.2 |
| [11] | [10] | Hijma P, Heldens S, Scolcco A, 等 | Optimization Techniques for GPU Programming | [J] | ACM Computing Surveys, 2023, 55(11): 1-81 | 2023 | GPU编程优化技术综述，通过大量文献分析总结私有化缓存、warp级归约等降低原子竞争的方法 | §1.2 |
| [12] | [15] | Zhang W, Zhao C, Peng L, 等 | Boosting Performance and QoS for Concurrent GPU B+trees by Combining-Based Synchronization | [C] | Proceedings of the 28th ACM SIGPLAN Annual Symposium on Principles and Practice of Parallel Programming. New York: ACM, 2023: 1-13 | 2023 | 提出基于请求合并的GPU B+树索引同步策略，通过减少重复原子操作降低竞争开销，在NVIDIA A100平台获得高吞吐性能 | §1.2 |
| [13] | [17] | Mellor-Crummey J M, Scott M L | Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors | [J] | ACM Transactions on Computer Systems, 1991, 9(1): 21-65 | 1991 | 系统分类五种栅栏同步算法（集中式、树形、传播、锦标赛和MCS），提出感知反转集中式栅栏与带本地自旋的静态树形栅栏 | §1.2 |
| [14] | [27] | Hensgen D, Finkel R, Manber U | Two Algorithms for Barrier Synchronization | [J] | International Journal of Parallel Programming, 1988, 17(1): 1-17 | 1988 | 最早对基于计数器的集中式栅栏算法进行形式化描述与分析，提出感知反转技术避免栅栏重用时的显式重置 | §1.3 |
| [15] | [18] | Yew P C, Tzeng N F, Lawrie D H | Distributing Hot-Spot Addressing in Large-Scale Multiprocessors | [J] | IEEE Transactions on Computers, 1987, C-36(4): 388-395 | 1987 | 最早提出软件合并树（software combining tree）概念，通过树结构分散多处理器互连网络中的热点访问竞争 | §1.3 |
| [16] | [28] | Gupta R, Hill C R | A Scalable Implementation of Barrier Synchronization Using an Adaptive Combining Tree | [J] | International Journal of Parallel Programming, 1989, 18(3): 161-180 | 1989 | 最早提出自适应合并树栅栏算法，将线程组织为二叉树结构以分散竞争，并包含静态树与模糊栅栏概念 | §1.3 |
| [17] | [19] | Reenskaug T | Models-Views-Controllers | [R] | Palo Alto: Xerox PARC | 1979 | 首次提出MVC（模型-视图-控制器）架构模式的技术报告，是交互式软件系统架构设计的奠基性文献 | §1.3 |
| [18] | [22] | Eugster P T, Felber A, Guerraoui R, 等 | The Many Faces of Publish/Subscribe | [J] | ACM Computing Surveys, 2003, 35(2): 114-131 | 2003 | 全面综述发布/订阅通信范式的各种变体与实现方案，是事件驱动架构设计的核心参考文献 | §1.3 |

---

## 待后续章节引用（尚未在正文中出现）

| 原编号 | 作者 | 标题 | 类型 | 出处/出版信息 | 年份 | 内容概要 |
|--------|------|------|------|-------------|------|---------|
| [7] | Fan J, Zhang Y, Li X, 等 | APEX: Asynchronous Parallel CPU-GPU Execution for Constrained GPUs | [EB/OL] | arXiv:2506.03296 | 2025 | 面向资源受限GPU的异步并行CPU-GPU执行框架 |
| [11] | Khairy M, Shen Z, Aamodt T M, 等 | Accel-Sim: An Extensible Simulation Framework for Validated GPU Modeling | [C] | ISCA 2020, pp. 473-486 | 2020 | 可扩展GPU仿真框架，支持GPU微架构级别的精确建模与验证 |
| [12] | Bakhoda A, Yuan G L, Fung W W L, 等 | Analyzing CUDA Workloads Using a Detailed GPU Simulator | [C] | ISPASS 2009, pp. 163-174 | 2009 | 开发GPGPU-Sim仿真器，实现CUDA工作负载的详细模拟分析 |
| [13] | Bertuletti M, Riedel S, Zhang Y, 等 | Fast Shared-Memory Barrier Synchronization for a 1024-Cores RISC-V Many-Core Cluster | [C] | SAMOS 2023, pp. 241-254 | 2023 | 面向千核RISC-V众核集群的快速共享内存栅栏同步方案 |
| [20] | Fowler M | Patterns of Enterprise Application Architecture | [M] | Boston: Addison-Wesley | 2002 | 企业应用架构模式经典著作，系统总结MVC、分层架构等软件架构设计模式 |
| [21] | Gamma E, Helm R, Johnson R, 等 | Design Patterns: Elements of Reusable Object-Oriented Software | [M] | Boston: Addison-Wesley | 1994 | GoF设计模式经典著作，定义观察者模式、策略模式等23种面向对象可复用设计模式 |
| [23] | Banks J, Carson J S, Nelson B L, 等 | Discrete-Event System Simulation | [M] | 5th ed. Upper Saddle River: Pearson | 2010 | 离散事件系统仿真经典教材，系统讲解事件驱动仿真引擎、时钟推进策略与仿真验证方法 |
| [24] | World Wide Web Consortium | HTML5 Specification | [S] | Cambridge: W3C | 2014 | HTML5国际标准规范，定义Web前端界面语义化标记、Canvas绘图与离线存储等核心能力 |
| [25] | World Wide Web Consortium | Cascading Style Sheets Level 3 Specification | [S] | Cambridge: W3C | 2011 | CSS3国际标准规范，定义布局、动画、过渡等界面样式与交互效果的标准接口 |
| [26] | Flanagan D | JavaScript: The Definitive Guide | [M] | 7th ed. Sebastopol: O'Reilly Media | 2020 | JavaScript语言权威指南，系统讲解JS异步编程模型、事件循环、DOM操作及前端状态管理 |
