# AHE-MRTA için Güncel Karşılaştırma Yöntemleri
## Recent Baseline Methods for Fair Comparison with AHE-MRTA

Bu dosya, ana proje dosyasındaki AHE-MRTA deney planına eklenen güncel karşılaştırma yöntemlerini ayrıntılandırır. Ana proje dosyası kısa tutulmalı; bu ek dosya ise seçilen yöntemlerin bibliyografik bilgilerini, metodolojik özünü, matematiksel uyarlamasını, ROS 2/Gazebo benchmark sistemine nasıl aktarılacağını ve Claude Code için uygulanabilir kod iskeletlerini içerir.

Ana dosyada bu ek dosyaya şu adla yönlendirme yapılmalıdır:

```text
ahe_mrta_recent_comparison_methods.md
```

---

# 1. Bu Dosyanın Amacı

AHE-MRTA'nın RA-L/Q1 SCI düzeyi bir makale olarak savunulabilmesi için yalnızca klasik baseline yöntemleriyle değil, son yıllarda yayımlanmış güçlü MRTA yöntem aileleriyle de karşılaştırılması gerekir. Bu nedenle üç güncel yöntem seçilmiştir:

1. **BiG-MRTA / Online Weighted Bipartite Graph MRTA**
2. **RoSTAM / Robust and Self-Adaptive Task Allocation for Multi-Robot Teams**
3. **Consensus-Based Fast and Energy-Efficient MRTA / DBTA**

Bu üç yöntem AHE-MRTA'nın üç farklı iddiasını test eder:

| AHE-MRTA iddiası | Test eden karşılaştırma yöntemi |
|---|---|
| Online ve hızlı görev atama | BiG-MRTA |
| Adaptif ve dinamik MRTA davranışı | RoSTAM |
| Düşük veri paylaşımlı / communication-efficient görev atama | Consensus-Based DBTA |

---

# 2. Yöntem Seçim Kriterleri

Yöntemler şu ölçütlere göre seçilmiştir:

| Kriter | Açıklama |
|---|---|
| Güncellik | Son 6 yıl içindeki dergi makalelerine öncelik verilmiştir. |
| MRTA yakınlığı | Doğrudan multi-robot task allocation problemiyle ilişkili olmalıdır. |
| Deneysel adalet | Aynı görev havuzu, robot durumu, seed seti ve Nav2 path cost yapısıyla çalıştırılabilir olmalıdır. |
| AHE'yi test etme gücü | AHE'nin online, adaptif, düşük iletişimli ve failure-aware iddialarından en az birini zorlamalıdır. |
| Kodlanabilirlik | ROS 2/Gazebo benchmark sisteminde yeniden uygulanabilir bir algoritmik özü olmalıdır. |
| Hakem ikna gücü | RA-L/Q1 hakemlerinin bekleyebileceği güçlü baseline ailelerini temsil etmelidir. |

---

# 3. Table 1 — Compact Method Characterization

Ana makalede Table 1 sade tutulacaktır. DOI, yıl ve dergi bilgileri her yöntemin kendi bibliyografik bilgi bölümünde verilir; ana Table 1 yalnızca yöntemlerin deneysel karakterini özetler.

| Method name | Online? | Adaptive? | Distributed/decentralized? |
|---|---|---|---|
| BiG-MRTA / Online Weighted Bipartite Graph MRTA | Yes | No/limited | Yes, suitable for decentralized deployment |
| RoSTAM-EA / Self-Adaptive Online MRTA | Yes | Yes | No/centralized evolutionary planner |
| Consensus-DBTA / Consensus-Based MRTA | Yes | Partly | Yes |

## 3.1. Bibliographic note for implementation

```text
BiG-MRTA:
  Journal: Robotics and Autonomous Systems
  Year: 2022
  DOI: 10.1016/j.robot.2021.103905

RoSTAM:
  Journal: Intelligent Decision Technologies
  Year: 2024
  DOI: 10.3233/IDT-230693

Consensus-DBTA:
  Journal: Robotics and Autonomous Systems
  Year: 2023
  DOI: 10.1016/j.robot.2022.104270
```

Not: Ana makale tablosunda fazla kolon kullanılmaması için bibliyografik ayrıntılar bu ek dosyada tutulur.

# 4. Method 1: BiG-MRTA
## Online Weighted Bipartite Graph MRTA

## 4.1. Bibliographic Information

```text
Authors: Payam Ghassemi and Souma Chowdhury
Year: 2022
Journal: Robotics and Autonomous Systems
Volume: 147
Article number: 103905
DOI: 10.1016/j.robot.2021.103905
```

## 4.2. Original Problem Setting

BiG-MRTA, SR-ST sınıfındaki MRTA problemleri için geliştirilmiştir. Yöntem özellikle şu özellikleri aynı anda ele alır:

```text
Single-robot tasks
Single-task robots
Dynamic task arrival
Task deadlines
Robot range constraints
Robot payload constraints
Multiple tours per robot
```

Orijinal makalede yöntem, çoklu UAV'lerin sel felaketi bağlamında kurbanlara yardım kiti ulaştırması senaryosu üzerinden test edilir. Bu bağlam AHE-MRTA'nın dinamik denetim, görev yoğunluğu, deadline ve robot kısıtları içeren senaryolarıyla uyumludur.

## 4.3. Core Methodology

BiG-MRTA üç ana adımdan oluşur:

```text
1. Bipartite graph construction
2. Incentive-based edge weight assignment
3. Maximum weighted graph matching
```

Her karar turunda robotlar ve aktif görevler arasında bir bipartite graph kurulur:

```text
G(t) = (R, T(t), E)
```

Burada:

```text
R = robot kümesi
T(t) = t anındaki aktif görev kümesi
E = uygulanabilir robot-görev kenarları
```

Her kenar, robotun ilgili görevi seçmesi durumunda oluşacak incentive değerine göre ağırlıklandırılır.

## 4.4. Original Incentive Logic

Orijinal çalışmanın temel incentive fonksiyonu, görevin deadline öncesi tamamlanabilirliğini ve robotun görevi tamamladıktan sonra depoya dönebilecek yeterli menzile sahip olup olmadığını birlikte ele alır.

AHE-MRTA benchmark'ına uyarlanmış gösterim:

```text
w_ij(t) = max(0, remaining_range_i_after_task_j - ε) · exp(-arrival_time_ij / α), if arrival_time_ij ≤ deadline_j
w_ij(t) = 0, otherwise
```

Burada:

```text
w_ij(t) = robot i ile görev j arasındaki bigraph edge weight
remaining_range_i_after_task_j = robot i'nin görev j ve dönüşten sonra kalan menzili
ε = güvenlik toleransı
α = zaman ölçekleme katsayısı
arrival_time_ij = robot i'nin görev j'yi tamamlayacağı tahmini zaman
deadline_j = görev j'nin son tamamlanma zamanı
```

AHE-MRTA TurtleBot/Nav2 benchmark'ında UAV menzili yerine şu karşılıklar kullanılabilir:

```text
remaining_range_i_after_task_j → simulated_battery_margin_i_after_task_j
arrival_time_ij → Nav2 path time estimate + queue delay
payload constraint → max_queue_capacity or max_tasks_per_replan_window
```

## 4.5. Adaptation to AHE-MRTA Benchmark

Orijinal BiG-MRTA her robot için myopic, yani bir karar turunda bir sonraki görevi seçmeye eğilimlidir. AHE-MRTA benchmark'ında robotlara görev kuyrukları gönderildiği için yöntem şu şekilde uyarlanmalıdır:

```text
BiG-MRTA-AHE adaptation = repeated maximum weighted bipartite matching + local insertion ordering
```

Uyarlama akışı:

```text
1. Aktif görevleri ve uygun robotları al.
2. Her robot-görev çifti için feasibility kontrolü yap.
3. Deadline ve batarya/menzil kısıtını sağlayan çiftler için incentive weight hesapla.
4. Maximum weighted matching ile her turda robotlara en fazla bir görev ata.
5. Atanan görevleri aktif havuzdan çıkar.
6. Robot başına kuyruk kapasitesi dolana veya görev kalmayana kadar tekrarla.
7. Her robotun görevlerini local insertion heuristic ile sırala.
```

Bu uyarlama, AHE-MRTA'nın çok görevli robot kuyruğu yapısıyla BiG-MRTA'nın graph matching mantığını uyumlu hale getirir.

## 4.6. Python-Style Implementation Skeleton

Aşağıdaki kod doğrudan makaledeki kod değildir. AHE-MRTA benchmark sistemi için yeniden uygulanabilir bir baseline iskeletidir.

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import numpy as np
from scipy.optimize import linear_sum_assignment

@dataclass
class RobotState:
    robot_id: str
    pose: Tuple[float, float]
    battery: float
    available: bool
    queue: List[str]
    failure_risk: float = 0.0

@dataclass
class TaskState:
    task_id: str
    position: Tuple[float, float]
    priority: int
    activation_time: float
    deadline: float
    service_time: float
    active: bool = True

class BigMRTABaseline:
    def __init__(self, alpha: float = 60.0, epsilon: float = 0.05,
                 max_queue_size: int = 5):
        self.alpha = alpha
        self.epsilon = epsilon
        self.max_queue_size = max_queue_size

    def estimate_path_cost(self, robot: RobotState, task: TaskState) -> float:
        # Replace with Nav2 path length or cached costmap path cost.
        dx = robot.pose[0] - task.position[0]
        dy = robot.pose[1] - task.position[1]
        return math.sqrt(dx * dx + dy * dy)

    def estimate_arrival_time(self, robot: RobotState, task: TaskState,
                              current_time: float, nominal_speed: float = 0.25) -> float:
        path_length = self.estimate_path_cost(robot, task)
        queue_delay = len(robot.queue) * 10.0
        return current_time + queue_delay + path_length / max(nominal_speed, 1e-6) + task.service_time

    def battery_margin_after_task(self, robot: RobotState, task: TaskState) -> float:
        path_cost = self.estimate_path_cost(robot, task)
        estimated_energy = 0.01 * path_cost
        return robot.battery - estimated_energy

    def incentive(self, robot: RobotState, task: TaskState, current_time: float) -> float:
        if not robot.available or not task.active:
            return 0.0
        if len(robot.queue) >= self.max_queue_size:
            return 0.0

        arrival_time = self.estimate_arrival_time(robot, task, current_time)
        if arrival_time > task.deadline:
            return 0.0

        margin = self.battery_margin_after_task(robot, task)
        if margin <= self.epsilon:
            return 0.0

        priority_bonus = 1.0 + 0.1 * task.priority
        return max(0.0, margin - self.epsilon) * math.exp(-arrival_time / self.alpha) * priority_bonus

    def build_weight_matrix(self, robots: List[RobotState], tasks: List[TaskState],
                            current_time: float) -> np.ndarray:
        W = np.zeros((len(robots), len(tasks)))
        for i, robot in enumerate(robots):
            for j, task in enumerate(tasks):
                W[i, j] = self.incentive(robot, task, current_time)
        return W

    def allocate(self, robots: List[RobotState], tasks: List[TaskState],
                 current_time: float) -> Dict[str, List[str]]:
        queues = {r.robot_id: list(r.queue) for r in robots}
        remaining_tasks = [t for t in tasks if t.active]
        local_robots = [RobotState(**vars(r)) for r in robots]

        while remaining_tasks:
            W = self.build_weight_matrix(local_robots, remaining_tasks, current_time)
            if np.max(W) <= 0.0:
                break

            # scipy solves minimization, so maximize W by minimizing -W.
            row_ind, col_ind = linear_sum_assignment(-W)
            assigned_task_ids = set()

            for r_idx, t_idx in zip(row_ind, col_ind):
                if W[r_idx, t_idx] <= 0.0:
                    continue
                robot = local_robots[r_idx]
                task = remaining_tasks[t_idx]
                if len(queues[robot.robot_id]) < self.max_queue_size:
                    queues[robot.robot_id].append(task.task_id)
                    robot.queue.append(task.task_id)
                    assigned_task_ids.add(task.task_id)

            if not assigned_task_ids:
                break
            remaining_tasks = [t for t in remaining_tasks if t.task_id not in assigned_task_ids]

        return queues
```

## 4.7. Fairness Conditions

| Koşul | Uygulama |
|---|---|
| Aynı görev havuzu | AHE ile aynı `TaskPool` kullanılmalı. |
| Aynı Nav2 path cost | Mesafe yerine mümkünse aynı cached Nav2 cost kullanılmalı. |
| Aynı deadline | Deadline tanımları değiştirilmemeli. |
| Aynı batarya modeli | Simulated battery state tüm yöntemlerde aynı olmalı. |
| Aynı seed | Görev aktivasyonları ve robot failure olayları aynı seed ile üretilmeli. |
| Aynı replan tetikleyici | Yeni görev, failure, stuck ve deadline riski aynı olay sistemiyle çalışmalı. |

## 4.8. Expected Strengths and Weaknesses

| Güçlü yön | Zayıf yön |
|---|---|
| Online ve hızlıdır. | Myopic kararlar uzun vadeli workload balance açısından zayıf kalabilir. |
| Deadline ve feasibility mantığı güçlüdür. | Cooperation/suppression gibi açıklanabilir heuristic etkileşimi yoktur. |
| Graph matching hakem için güçlü baseline'dır. | Dinamik congestion ve failure recovery AHE kadar bağlam-duyarlı değildir. |

---

# 5. Method 2: RoSTAM
## Robust and Self-Adaptive Task Allocation for Multi-Robot Teams

## 5.1. Bibliographic Information

```text
Authors: Muhammad Usman Arif and Sajjad Haider
Year: 2024
Journal: Intelligent Decision Technologies
Volume: 18
Issue: 2
Pages: 1053-1076
DOI: 10.3233/IDT-230693
```

## 5.2. Original Problem Setting

RoSTAM, dinamik MRTA senaryolarında robot failure, new task arrival, team expansion ve problem distribution değişimleri gibi çevresel değişimlere uyum sağlayan self-adaptive bir task allocation framework olarak sunulur.

Yöntemin hedeflediği problem aileleri:

```text
ST-SR-TA
ST-MR-TA
Dynamic robot failure
New task arrival
Team expansion
Task expansion
Online replanning
```

AHE-MRTA'nın bu yöntemle karşılaştırılması özellikle önemlidir çünkü iki yöntem de adaptasyon iddiası taşır. Fark şudur:

```text
RoSTAM = evolutionary self-adaptation
AHE-MRTA = heuristic dominance/cooperation/suppression based adaptation
```

## 5.3. Original Mathematical Core

RoSTAM, her robot için bir görev sırası üretir. Robot r'nin görevlere bağlı tur maliyeti şu mantıkla hesaplanır:

```text
Tour_r = D(t0, t_r1) + Σ_k D(t_r(k-1), t_rk) + D(t_rm, t0)
```

Takım düzeyindeki amaç fonksiyonu makespan minimizasyonudur:

```text
TourTime(S) = max_r Tour_r
```

```text
Objective = minimize TourTime(S)
```

AHE-MRTA benchmark'ında bu amaç fonksiyonu genişletilmelidir:

```text
Fitness = μ1 · makespan
        + μ2 · average_task_delay
        + μ3 · deadline_violation_rate
        + μ4 · workload_variance
        + μ5 · failure_penalty
        + μ6 · reallocation_penalty
```

Bu genişletme gereklidir çünkü AHE-MRTA yalnızca makespan değil, deadline, workload balance, recovery ve allocation instability gibi RA-L açısından daha güçlü metrikleri de raporlayacaktır.

## 5.4. Chromosome Representation

RoSTAM iki parçalı kromozom kullanır:

```text
chromosome = [task_permutation | robot_partition_counts]
```

Örnek:

```text
Task permutation:       [5, 2, 8, 1, 4, 7, 3]
Robot partition counts: [2, 3, 2]
```

Bu durumda:

```text
robot_1 = [5, 2]
robot_2 = [8, 1, 4]
robot_3 = [7, 3]
```

AHE-MRTA benchmark'ında ST-SR-TA kullanılacağı için her görev tek robot tarafından tamamlanacak şekilde temsil edilmelidir. Multi-robot task instance mantığı şimdilik gerekli değildir.

## 5.5. Evolutionary Operators

AHE-MRTA benchmark'ına uygun RoSTAM-EA baseline için önerilen operatörler:

| Bileşen | Uygulama |
|---|---|
| Selection | Tournament selection |
| Crossover | Ordered crossover for task permutation |
| Mutation 1 | Swap mutation |
| Mutation 2 | Inversion mutation |
| Partition mutation | Robot partition count üzerinde küçük kaydırma |
| Diversity injection | Her jenerasyonda popülasyonun %20'sini yeni rastgele çözümlerle değiştir |
| Adaptive penalty | Feasibility durumuna göre ceza katsayısını artır/azalt |
| Online reformulation | Failure veya new task arrival durumunda son popülasyonu seed olarak kullan |

## 5.6. Online Plan Reformulation

RoSTAM'ın AHE benchmark'ındaki en önemli kısmı online plan reformulation olmalıdır.

Olay olduğunda:

```text
1. Tamamlanmış görevleri tüm kromozomlardan çıkar.
2. Başarısız robotu robot listesinden çıkar.
3. Başarısız robotun tamamlanmamış görevlerini unallocated task pool'a geri koy.
4. Yeni görevleri task pool'a ekle.
5. Son popülasyonu yeni çözüm uzayına uyacak şekilde tamir et.
6. EA'yı önceki popülasyonla yeniden başlat.
```

Bu yapı AHE-MRTA'nın event-triggered replanning yapısıyla adil biçimde karşılaştırılabilir.

## 5.7. Python-Style Implementation Skeleton

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple
import random
import math
import numpy as np

@dataclass
class Candidate:
    permutation: List[str]
    partitions: List[int]
    fitness: float = float("inf")

class RoSTAMEABaseline:
    def __init__(self, population_size: int = 50, generations: int = 50,
                 elite_count: int = 2, diversity_rate: float = 0.20,
                 initial_penalty: float = 100.0):
        self.population_size = population_size
        self.generations = generations
        self.elite_count = elite_count
        self.diversity_rate = diversity_rate
        self.penalty = initial_penalty
        self.last_population: List[Candidate] = []

    def build_candidate(self, task_ids: List[str], robot_count: int) -> Candidate:
        perm = task_ids[:]
        random.shuffle(perm)
        partitions = self.random_partitions(len(perm), robot_count)
        return Candidate(perm, partitions)

    def random_partitions(self, n_tasks: int, n_robots: int) -> List[int]:
        counts = [0] * n_robots
        for _ in range(n_tasks):
            counts[random.randrange(n_robots)] += 1
        return counts

    def decode(self, candidate: Candidate, robot_ids: List[str]) -> Dict[str, List[str]]:
        queues = {r: [] for r in robot_ids}
        idx = 0
        for robot_id, count in zip(robot_ids, candidate.partitions):
            queues[robot_id] = candidate.permutation[idx:idx + count]
            idx += count
        return queues

    def path_cost(self, robot_id: str, task_a: str, task_b: str, cost_matrix: Dict[Tuple[str, str], float]) -> float:
        return cost_matrix.get((task_a, task_b), cost_matrix.get((task_b, task_a), 1e6))

    def evaluate(self, candidate: Candidate, robot_ids: List[str], depot_id: str,
                 cost_matrix: Dict[Tuple[str, str], float], task_deadlines: Dict[str, float],
                 current_time: float) -> float:
        queues = self.decode(candidate, robot_ids)
        tour_costs = []
        deadline_violations = 0
        completed_counts = []

        for robot_id, queue in queues.items():
            if not queue:
                tour_costs.append(0.0)
                completed_counts.append(0)
                continue

            elapsed = current_time
            cost = self.path_cost(robot_id, depot_id, queue[0], cost_matrix)
            elapsed += cost
            if elapsed > task_deadlines.get(queue[0], float("inf")):
                deadline_violations += 1

            for a, b in zip(queue[:-1], queue[1:]):
                step = self.path_cost(robot_id, a, b, cost_matrix)
                cost += step
                elapsed += step
                if elapsed > task_deadlines.get(b, float("inf")):
                    deadline_violations += 1

            cost += self.path_cost(robot_id, queue[-1], depot_id, cost_matrix)
            tour_costs.append(cost)
            completed_counts.append(len(queue))

        makespan = max(tour_costs) if tour_costs else 0.0
        workload_variance = float(np.var(completed_counts)) if completed_counts else 0.0
        return makespan + self.penalty * deadline_violations + 5.0 * workload_variance

    def ordered_crossover(self, p1: Candidate, p2: Candidate) -> Candidate:
        n = len(p1.permutation)
        a, b = sorted(random.sample(range(n), 2))
        child_perm = [None] * n
        child_perm[a:b] = p1.permutation[a:b]
        fill = [x for x in p2.permutation if x not in child_perm]
        ptr = 0
        for i in range(n):
            if child_perm[i] is None:
                child_perm[i] = fill[ptr]
                ptr += 1
        child_partitions = p1.partitions[:] if random.random() < 0.5 else p2.partitions[:]
        return Candidate(child_perm, child_partitions)

    def mutate(self, c: Candidate) -> None:
        if len(c.permutation) >= 2 and random.random() < 0.4:
            i, j = random.sample(range(len(c.permutation)), 2)
            c.permutation[i], c.permutation[j] = c.permutation[j], c.permutation[i]

        if len(c.permutation) >= 4 and random.random() < 0.2:
            i, j = sorted(random.sample(range(len(c.permutation)), 2))
            c.permutation[i:j] = reversed(c.permutation[i:j])

        if random.random() < 0.3 and len(c.partitions) >= 2:
            src = random.randrange(len(c.partitions))
            dst = random.randrange(len(c.partitions))
            if src != dst and c.partitions[src] > 0:
                c.partitions[src] -= 1
                c.partitions[dst] += 1

    def update_adaptive_penalty(self, population: List[Candidate], feasible_flags: List[bool]) -> None:
        # A simplified version of RoSTAM's adaptive penalty logic.
        if len(feasible_flags) < 10:
            return
        last = feasible_flags[-10:]
        if all(not f for f in last):
            self.penalty *= 1.15
        elif all(f for f in last):
            self.penalty *= 0.85

    def reformulate_population(self, active_task_ids: List[str], available_robot_ids: List[str]) -> List[Candidate]:
        active_set = set(active_task_ids)
        repaired = []
        for cand in self.last_population:
            perm = [t for t in cand.permutation if t in active_set]
            missing = [t for t in active_task_ids if t not in perm]
            random.shuffle(missing)
            perm.extend(missing)
            partitions = self.random_partitions(len(perm), len(available_robot_ids))
            repaired.append(Candidate(perm, partitions))
        return repaired[:self.population_size]

    def allocate(self, active_task_ids: List[str], available_robot_ids: List[str], depot_id: str,
                 cost_matrix: Dict[Tuple[str, str], float], task_deadlines: Dict[str, float],
                 current_time: float, use_reformulation: bool = True) -> Dict[str, List[str]]:
        if use_reformulation and self.last_population:
            population = self.reformulate_population(active_task_ids, available_robot_ids)
        else:
            population = []

        while len(population) < self.population_size:
            population.append(self.build_candidate(active_task_ids, len(available_robot_ids)))

        feasible_history = []
        for _ in range(self.generations):
            for cand in population:
                cand.fitness = self.evaluate(cand, available_robot_ids, depot_id, cost_matrix,
                                             task_deadlines, current_time)
            population.sort(key=lambda c: c.fitness)
            feasible_history.append(population[0].fitness < self.penalty)
            self.update_adaptive_penalty(population, feasible_history)

            next_pop = population[:self.elite_count]
            while len(next_pop) < self.population_size:
                p1, p2 = random.sample(population[:max(5, self.population_size // 2)], 2)
                child = self.ordered_crossover(p1, p2)
                self.mutate(child)
                next_pop.append(child)

            # Diversity injection: replace 20% with random candidates except elites.
            inject_count = int(self.diversity_rate * self.population_size)
            for _ in range(inject_count):
                idx = random.randrange(self.elite_count, self.population_size)
                next_pop[idx] = self.build_candidate(active_task_ids, len(available_robot_ids))

            population = next_pop

        population.sort(key=lambda c: c.fitness)
        self.last_population = population
        return self.decode(population[0], available_robot_ids)
```

## 5.8. Fairness Conditions

| Koşul | Uygulama |
|---|---|
| Zaman sınırı | RoSTAM-EA için `max_generation` veya `max_decision_time` sınırı konmalı. |
| Aynı seed | EA stochastic olduğu için her seed için aynı görev/failure dizisi kullanılmalı. |
| Aynı görev havuzu | AHE ile aynı aktif görev listesi kullanılmalı. |
| Aynı olay tetikleyicileri | Robot failure ve new task arrival AHE ile aynı anda oluşmalı. |
| Aynı maliyet matrisi | Nav2 path cost veya aynı Öklid mesafesi kullanılmalı. |
| Aynı replanning politikası | Event-based replanning ana karşılaştırma için kullanılmalı. |

## 5.9. Expected Strengths and Weaknesses

| Güçlü yön | Zayıf yön |
|---|---|
| Adaptif ve dinamik MRTA için güçlü rakiptir. | EA tabanlı olduğu için decision latency AHE'den yüksek olabilir. |
| Failure ve new task arrival senaryolarında anlamlıdır. | Sonuçlar stochastic olduğu için daha fazla tekrar gerekir. |
| Hakem açısından “adaptive baseline” boşluğunu kapatır. | ROS 2 gerçek zamanlı çalışma için süre sınırı şarttır. |

---

# 6. Method 3: Consensus-Based DBTA
## Consensus-Based Fast and Energy-Efficient Multi-Robot Task Allocation

## 6.1. Bibliographic Information

```text
Authors: Prabhat Mahato, Sudipta Saha, Chayan Sarkar, Md. Shaghil
Year: 2023
Journal: Robotics and Autonomous Systems
Volume: 159
Article number: 104270
DOI: 10.1016/j.robot.2022.104270
```

## 6.2. Original Problem Setting

Bu çalışma, merkezi altyapının olmadığı ve robotlar arası iletişimin ad-hoc network üzerinden yapıldığı dinamik MRTA durumlarına odaklanır. Yöntem özellikle communication-efficient task allocation iddiası taşır.

Orijinal çalışmada üç strateji açıklanır:

| Strateji | Açıklama |
|---|---|
| **AATA** | All-to-all data sharing based task allocation. Her robot tüm görevler için bid paylaşır. Kaliteli ama iletişim maliyeti yüksektir. |
| **IBTA** | Independent bidding task allocation. Her seferinde tek görev için consensus yapılır. Daha az iletişim ama greedy davranış nedeniyle kalite düşebilir. |
| **DBTA** | Dynamic bidding based task allocation. Robotlar en iyi birden fazla bid'i paylaşır. Varsayılan olarak DBTA2 kullanılır. Kalite ve iletişim maliyeti arasında denge sağlar. |

AHE-MRTA benchmark'ında temel baseline olarak **DBTA2** kullanılmalıdır.

## 6.3. Core Methodology

DBTA'nın ana fikri:

```text
Her robot tüm aktif görevler için bid üretir.
Robotlar yalnızca en güçlü birkaç bid'i paylaşır.
Consensus sürecinde daha yüksek bid görülen görevlerde gereksiz bid paylaşımı azaltılır.
Son karar, her görev için maksimum bid'i veren robota göre yapılır.
Priority 1 ve Priority 2 bid'leri kullanılarak robot başına çakışmasız görev ataması yapılır.
```

AHE-MRTA ile bağlantısı:

```text
AHE-MRTA düşük veri paylaşımlı merkezi-ekosistem mimarisi önerir.
Consensus-DBTA ise dağıtık consensus ile bilgi paylaşımını azaltmaya çalışır.
Bu nedenle communication footprint, allocation latency ve task quality açısından iyi bir karşılaştırma yöntemidir.
```

## 6.4. Bid Function for AHE-MRTA Benchmark

Orijinal çalışma utility/bid mantığı kullanır. AHE-MRTA benchmark'ında şu ortak bid fonksiyonu kullanılabilir:

```text
bid_ij(t) = a_p · priority_score_j
          + a_t · deadline_slack_score_ij
          + a_b · battery_margin_i
          - a_d · normalized_path_cost_ij
          - a_l · queue_load_i
          - a_f · failure_risk_i
```

Burada:

```text
priority_score_j = normalized priority of task j
deadline_slack_score_ij = 1 / (1 + max(0, estimated_arrival_ij - deadline_j))
battery_margin_i = normalized battery state of robot i
normalized_path_cost_ij = Nav2 path cost normalized to [0, 1]
queue_load_i = current queue length normalized by max_queue_size
failure_risk_i = robot reliability/failure penalty
```

## 6.5. Adaptation to ROS 2/Gazebo

Gerçek ST/Chaos communication protocol'ünü ROS 2 simülasyonunda birebir modellemek gerekmeyebilir. Adil ve uygulanabilir karşılaştırma için şu sadeleştirme önerilir:

```text
Consensus-DBTA-AHE adaptation:
- Her robot kendi bid listesini üretir.
- Robot başına yalnızca top-2 bid paylaşılmış gibi loglanır.
- Merkezi experiment runner bu bidleri toplar, fakat communication footprint top-2 bid varsayımıyla hesaplanır.
- Çakışmasız görev ataması DBTA priority rule ile yapılır.
```

Bu uyarlama, gerçek iletişim katmanını simüle etmeden yöntemin temel allocation mantığını ve düşük veri paylaşımı iddiasını test eder.

## 6.6. Python-Style Implementation Skeleton

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple
import math

@dataclass
class Bid:
    robot_id: str
    task_id: str
    value: float
    priority_rank: int

class ConsensusDBTABaseline:
    def __init__(self, top_k_bids: int = 2, max_queue_size: int = 5):
        self.top_k_bids = top_k_bids
        self.max_queue_size = max_queue_size

    def estimate_path_cost(self, robot, task) -> float:
        dx = robot.pose[0] - task.position[0]
        dy = robot.pose[1] - task.position[1]
        return math.sqrt(dx * dx + dy * dy)

    def estimate_arrival(self, robot, task, current_time: float, speed: float = 0.25) -> float:
        return current_time + self.estimate_path_cost(robot, task) / max(speed, 1e-6)

    def bid_value(self, robot, task, current_time: float) -> float:
        if not robot.available or not task.active:
            return float("-inf")
        if len(robot.queue) >= self.max_queue_size:
            return float("-inf")

        path_cost = self.estimate_path_cost(robot, task)
        arrival = self.estimate_arrival(robot, task, current_time)
        slack = max(0.0, task.deadline - arrival)

        priority_score = float(task.priority)
        deadline_score = 1.0 / (1.0 + max(0.0, arrival - task.deadline))
        battery_score = float(robot.battery)
        load_penalty = len(robot.queue) / max(1, self.max_queue_size)
        failure_penalty = getattr(robot, "failure_risk", 0.0)

        return (
            2.0 * priority_score
            + 3.0 * deadline_score
            + 1.0 * battery_score
            - 0.5 * path_cost
            - 2.0 * load_penalty
            - 3.0 * failure_penalty
        )

    def create_top_bids(self, robots, tasks, current_time: float) -> List[Bid]:
        all_bids: List[Bid] = []
        for robot in robots:
            robot_bids = []
            for task in tasks:
                value = self.bid_value(robot, task, current_time)
                if value != float("-inf"):
                    robot_bids.append((task.task_id, value))
            robot_bids.sort(key=lambda x: x[1], reverse=True)
            for rank, (task_id, value) in enumerate(robot_bids[:self.top_k_bids], start=1):
                all_bids.append(Bid(robot.robot_id, task_id, value, rank))
        return all_bids

    def consensus_max_bids(self, bids: List[Bid]) -> Dict[str, Bid]:
        # Simulated consensus result: for each task, keep the highest bid.
        winners: Dict[str, Bid] = {}
        for bid in bids:
            if bid.task_id not in winners or bid.value > winners[bid.task_id].value:
                winners[bid.task_id] = bid
        return winners

    def allocate_from_consensus(self, winners: Dict[str, Bid]) -> Dict[str, List[str]]:
        allocation: Dict[str, List[str]] = {}
        allocated_robots = set()

        # Priority 1 bids first.
        for task_id, bid in sorted(winners.items(), key=lambda x: x[1].priority_rank):
            if bid.priority_rank == 1 and bid.robot_id not in allocated_robots:
                allocation.setdefault(bid.robot_id, []).append(task_id)
                allocated_robots.add(bid.robot_id)

        # Priority 2 bids next, only if robot not already allocated in this round.
        for task_id, bid in sorted(winners.items(), key=lambda x: x[1].priority_rank):
            if bid.priority_rank == 2 and bid.robot_id not in allocated_robots:
                allocation.setdefault(bid.robot_id, []).append(task_id)
                allocated_robots.add(bid.robot_id)

        return allocation

    def allocate(self, robots, tasks, current_time: float) -> Dict[str, List[str]]:
        queues = {r.robot_id: list(r.queue) for r in robots}
        remaining_tasks = [t for t in tasks if t.active]

        while remaining_tasks:
            bids = self.create_top_bids(robots, remaining_tasks, current_time)
            if not bids:
                break
            winners = self.consensus_max_bids(bids)
            round_allocation = self.allocate_from_consensus(winners)
            if not round_allocation:
                break

            assigned = set()
            for robot_id, task_ids in round_allocation.items():
                for task_id in task_ids:
                    if len(queues[robot_id]) < self.max_queue_size:
                        queues[robot_id].append(task_id)
                        assigned.add(task_id)

            if not assigned:
                break
            remaining_tasks = [t for t in remaining_tasks if t.task_id not in assigned]

        return queues

    def estimate_communication_footprint(self, robot_count: int, bid_size_bytes: int = 16) -> int:
        # Top-k bid sharing approximation.
        return robot_count * self.top_k_bids * bid_size_bytes
```

## 6.7. Fairness Conditions

| Koşul | Uygulama |
|---|---|
| Communication footprint | DBTA için robot başına yalnızca top-2 bid paylaşıldığı varsayımı loglanmalı. |
| Aynı bid bileşenleri | Priority, deadline, path cost, battery ve load bileşenleri AHE cost bileşenleriyle aynı veriden türetilmeli. |
| Aynı görev aktivasyonu | Dynamic task arrival aynı seed setiyle olmalı. |
| Aynı failure olayları | Robot failure ve stuck olayları aynı zamanda oluşmalı. |
| Aynı queue kapasitesi | Robot başına maksimum görev kuyruğu tüm yöntemlerde aynı olmalı. |

## 6.8. Expected Strengths and Weaknesses

| Güçlü yön | Zayıf yön |
|---|---|
| Düşük iletişim yükü açısından güçlü baseline'dır. | Task quality, AHE veya RoSTAM kadar güçlü olmayabilir. |
| Dynamic task arrival için uygundur. | Cooperation/suppression veya dominance evolution yoktur. |
| Communication footprint metriğini anlamlı hale getirir. | Gerçek ST/Chaos protokolünü ROS 2'de birebir modellemek ayrı bir çalışma gerektirir. |

---

# 7. Final Comparison Set for AHE-MRTA

Deney matrisinde kullanılan yöntem seti (ana proje dosyası §10.2.3 baz alınır):

| Grup | Yöntem | Kısa ad | Rol |
|---|---|---|---|
| Proposed method | AHE_MRTA_V3 (14 mekanizma) | `ahe_mrta_v3` | Önerilen yöntem — tüm 3 senaryoda Compl 1. sıra |
| Recent online graph | BiG-MRTA | `big_mrta` | Online weighted bipartite graph |
| Recent self-adaptive EA | RoSTAM-EA | `rostam_ea` | Evolutionary self-adaptive MRTA |
| Recent comm-efficient | Consensus-DBTA | `consensus_dbta` | Düşük iletişimli consensus-based MRTA |
| V3 Ablation | no bipartite matching | `ahe_mrta_v3_no_bipartite` | M1 katkısı |
| V3 Ablation | no dense-init delegation | `ahe_mrta_v3_no_dense_init` | M17 katkısı |
| V3 Ablation | no recovery turbo | `ahe_mrta_v3_no_recovery` | M8+M11 katkısı |
| V3 Ablation | fixed ecosystem weights | `ahe_mrta_v3_fixed_weights` | Ekosistem harmanlama katkısı |

---

# 8. Senaryo–Yöntem Eşleştirmesi (güncel)

Tüm yöntemler tüm 3 senaryoda koşulur (3r/15g, 5 seed):

| Senaryo           | G1 (ahe_mrta_v3, big_mrta, rostam_ea, consensus_dbta) | G2 (4 V3 ablasyon varyantı) |
|---|---|---|
| robot_failure     | ✓ 5 seed × 4 = 20 deney | ✓ 5 seed × 4 = 20 deney |
| mixed_stress      | ✓ 5 seed × 4 = 20 deney | ✓ 5 seed × 4 = 20 deney |
| deadline_pressure | ✓ 5 seed × 4 = 20 deney | ✓ 5 seed × 4 = 20 deney |
| **Toplam**        | **60 deney** | **60 deney** |

Gazebo toplam: **120 deney** · Video: **12 adet** (seed=01 × 4 yöntem × 3 senaryo)

---

# 10. Unified Baseline Interface for Claude Code

Claude Code'a baseline yöntemlerini ortak bir arayüz üzerinden yazdırmak daha güvenli olur.

Önerilen dosya yapısı:

```text
ahe_task_allocator/
└── ahe_task_allocator/
    ├── baselines/
    │   ├── __init__.py
    │   ├── base_allocator.py
    │   ├── greedy_nearest.py
    │   ├── deadline_aware.py
    │   ├── auction_based.py
    │   ├── static_weighted.py
    │   ├── big_mrta.py
    │   ├── rostam_ea.py
    │   ├── consensus_dbta.py
    │   └── ahe_variants.py
    └── task_allocator_node.py
```

Ortak arayüz:

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class BaseAllocator(ABC):
    @abstractmethod
    def allocate(self, robots, tasks, context, current_time: float) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass
```

Experiment runner, yöntemi şu şekilde seçmelidir:

```python
ALLOCATOR_REGISTRY = {
    # G1 — Karşılaştırma
    "ahe_mrta_v3":                  AHEMRTAv3Allocator,
    "big_mrta":                     BigMRTAAllocator,
    "rostam_ea":                    RoSTAMEAAllocator,
    "consensus_dbta":               ConsensusDBTAAllocator,
    # G2 — Ablasyon
    "ahe_mrta_v3_no_bipartite":     AHEMRTAv3NoBipartiteAllocator,
    "ahe_mrta_v3_no_dense_init":    AHEMRTAv3NoDenseInitAllocator,
    "ahe_mrta_v3_no_recovery":      AHEMRTAv3NoRecoveryAllocator,
    "ahe_mrta_v3_fixed_weights":    AHEMRTAv3FixedWeightsAllocator,
}
```

---

# 11. Metrics to Compare These Methods

Eklenen yeni yöntemler nedeniyle metrik listesine özellikle şu metrikler vurgulu eklenmelidir:

| Metrik | Neden önemli? |
|---|---|
| `task_completion_rate` | BiG-MRTA ve AHE için temel başarı metriği |
| `average_task_delay` | Deadline ve online allocation başarısı |
| `deadline_violation_rate` | EDF ve BiG-MRTA ile adil kıyas |
| `total_travel_distance` | Greedy/Static/DBTA ile klasik maliyet kıyası |
| `workload_balance` | AHE ve RoSTAM için kritik |
| `failure_recovery_time` | AHE ve RoSTAM karşılaştırmasının ana metriği |
| `allocation_instability` | AHE event-triggered replanning katkısı |
| `mean_decision_latency` | AHE'nin hafiflik iddiası |
| `communication_footprint_bytes` | Consensus-DBTA ve AHE düşük veri paylaşımı kıyası |
| `replanning_frequency` | Continuous vs event-triggered replanning etkisi |
| `heuristic_dominance_evolution` | Yalnızca AHE için açıklanabilirlik metriği |

---

# 12. Claude Code Prompt: Recent Baseline Methods

Aşağıdaki prompt, ana proje fazları ilerledikten sonra Claude Code'a verilebilir.

```text
Implement the recent comparison baselines for the AHE-MRTA benchmark.

Read the supplementary file:
ahe_mrta_recent_comparison_methods.md

Implement the following baseline allocators under:
ahe_task_allocator/ahe_task_allocator/baselines/

1. big_mrta.py
   - Online weighted bipartite graph MRTA
   - Repeated maximum weighted matching
   - Incentive-based edge weights
   - Deadline and battery feasibility filtering

2. rostam_ea.py
   - RoSTAM-inspired evolutionary task allocation
   - Two-part chromosome representation
   - Ordered crossover, swap/inversion mutation
   - Adaptive penalty
   - Population diversity injection
   - Online plan reformulation after failures and new task arrivals

3. consensus_dbta.py
   - Consensus-based DBTA2 baseline
   - Each robot generates top-2 bids
   - Simulated consensus keeps maximum bid per task
   - Priority-1 then Priority-2 allocation rule
   - Log estimated communication footprint

All baselines must implement the same BaseAllocator interface:
allocate(robots, tasks, context, current_time) -> Dict[str, List[str]]

Fairness requirements:
- Use the same task pool.
- Use the same robot states.
- Use the same seed set.
- Use the same Nav2 path cost cache when available.
- Use the same failure and task arrival events.
- Log decision latency for every allocation call.
- Log communication footprint for every allocation call.
- Do not send global ecosystem state to robots.

Stop after implementation and provide:
- created files
- command to run unit tests
- sample allocation output
- expected CSV fields added for these baselines
```

---

# 13. RA-L Paper Reporting Text

Makalede kullanılabilecek kısa yöntem seçimi paragrafı:

```text
To evaluate AHE-MRTA against recent MRTA families, three additional journal-based baselines were selected. BiG-MRTA represents online weighted bipartite graph allocation under dynamic tasks and deadlines. RoSTAM represents self-adaptive evolutionary task allocation under new task arrivals and robot failures. Consensus-DBTA represents communication-efficient distributed bidding and consensus-based allocation. These methods allow AHE-MRTA to be assessed with respect to online allocation quality, adaptive robustness, decision latency, and communication footprint.
```

Türkçe karşılığı:

```text
AHE-MRTA'nın güncel MRTA yöntem aileleri karşısındaki performansını değerlendirmek için üç ek dergi tabanlı baseline seçilmiştir. BiG-MRTA, dinamik görevler ve deadline koşulları altında online weighted bipartite graph allocation çizgisini temsil eder. RoSTAM, yeni görev oluşumu ve robot arızaları altında self-adaptive evolutionary task allocation yaklaşımını temsil eder. Consensus-DBTA ise düşük iletişim yüküyle dağıtık bidding ve consensus-based allocation yaklaşımını temsil eder. Bu üç yöntem AHE-MRTA'nın online allocation quality, adaptive robustness, decision latency ve communication footprint açısından değerlendirilmesini sağlar.
```

---

# 14. Important Reporting Cautions

1. **RoSTAM stochastic olduğu için tek koşu ile raporlanmamalıdır.** En az 20 seed önerilir.
2. **Consensus-DBTA için gerçek ST/Chaos protokolü birebir simüle edilmiyorsa açıkça yazılmalıdır.** Bu çalışma için önerilen sürüm allocation-level DBTA adaptation'dır.
3. **BiG-MRTA'nın orijinal UAV range/payload yapısı TurtleBot/Nav2 için simulated battery ve queue capacity ile eşlenmelidir.** Bu eşleme yöntem bölümünde şeffaf yazılmalıdır.
4. **AHE her metrikte birinci çıkmak zorunda değildir.** Özellikle travel distance yerine robustness, recovery, workload balance, decision latency ve communication footprint üzerinden yorum yapılmalıdır.
5. **Ana makalede tüm kod ayrıntıları verilmemelidir.** Kod/pseudocode ve uyarlama ayrıntıları bu ek dosyada veya supplementary material/repository içinde tutulmalıdır.

