<template>
  <main class="page model-page">
    <TaskOverlay
      :visible="taskOverlayVisible"
      :task="overlayTask"
      title="后台任务运行中"
      eyebrow="模型训练"
      @cancel="cancelOverlayTask"
      @close="taskOverlayVisible = false"
    />

    <el-dialog
      v-model="paramDialogVisible"
      :title="activeParam?.title || '参数说明'"
      width="min(680px, calc(100vw - 32px))"
      class="param-detail-dialog"
      append-to-body
    >
      <div v-if="activeParam" class="param-detail">
        <p class="param-summary">{{ activeParam.short }}</p>
        <section>
          <strong>参数含义</strong>
          <p>{{ activeParam.meaning }}</p>
        </section>
        <section>
          <strong>调大/调小的影响</strong>
          <p>{{ activeParam.effect }}</p>
        </section>
        <section>
          <strong>本项目建议</strong>
          <p>{{ activeParam.suggestion }}</p>
        </section>
        <section v-if="activeParam.details?.length">
          <strong>关键理解</strong>
          <ul>
            <li v-for="item in activeParam.details" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
    </el-dialog>

    <section class="panel header-panel">
      <div>
        <strong>模型训练</strong>
        <p class="muted">当前只训练 CIFAR-10 数据集，分为 CNN 分类模型和 Triplet 度量学习模型两条路线。</p>
      </div>
      <div class="dataset-lock">
        <span>CIFAR-10</span>
        <small>50000 训练 / 10000 测试 / 10 类</small>
      </div>
    </section>

    <section class="dataset-panel panel">
      <div>
        <span class="eyebrow">固定训练数据</span>
        <h3>CIFAR-10 官方 Python 数据包</h3>
        <p class="muted">训练脚本读取同一个本地解包目录</p>
      </div>
      <div class="source-path">
        <span>数据源目录</span>
        <code>{{ CIFAR10_SRC }}</code>
      </div>
      <div class="dataset-facts">
        <span>32×32 RGB</span>
        <span>10 个类别</span>
        <span>60000 张图像</span>
      </div>
    </section>

    <section class="training-grid">
      <div class="panel training-card">
        <div class="training-head">
          <div>
            <span class="eyebrow">训练路线 1</span>
            <strong>CNN 分类模型</strong>
            <p class="muted">训练 CIFAR-ResNet18 分类模型，输出按参数命名的 .pt，作为深度特征基线。</p>
          </div>
          <span class="model-badge">CNN</span>
        </div>

        <el-form label-position="top" class="compact-form">
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <span class="param-label">Epoch <ParamInfo :info="parameterInfos.epochs" @open="openParamDialog('epochs')" /></span>
              </template>
              <el-input-number v-model="cnnForm.epochs" :min="1" :max="500" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Batch Size <ParamInfo :info="parameterInfos.batchSize" @open="openParamDialog('batchSize')" /></span>
              </template>
              <el-input-number v-model="cnnForm.batchSize" :min="16" :max="1024" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">学习率 <ParamInfo :info="parameterInfos.lr" @open="openParamDialog('lr')" /></span>
              </template>
              <el-input-number v-model="cnnForm.lr" :min="0.0001" :max="1" :step="0.01" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Workers <ParamInfo :info="parameterInfos.workers" @open="openParamDialog('workers')" /></span>
              </template>
              <el-input-number v-model="cnnForm.workers" :min="0" :max="16" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">权重衰减 WD <ParamInfo :info="parameterInfos.weightDecay" @open="openParamDialog('weightDecay')" /></span>
              </template>
              <el-input-number v-model="cnnForm.weightDecay" :min="0" :max="0.1" :step="0.0001" controls-position="right" />
            </el-form-item>
          </div>
          <div class="form-row">
            <div class="checkbox-with-info">
              <el-checkbox v-model="cnnForm.amp">使用 AMP 混合精度</el-checkbox>
              <ParamInfo :info="parameterInfos.amp" @open="openParamDialog('amp')" />
            </div>
            <el-button type="primary" :loading="starting" @click="trainCnn">开始训练 CNN</el-button>
          </div>
        </el-form>

        <div class="training-summary">
          <span>当前配置</span>
          <div>
            <span class="summary-item"><strong>{{ cnnForm.epochs }}</strong><small>Epoch</small></span>
            <span class="summary-item"><strong>{{ cnnForm.batchSize }}</strong><small>Batch</small></span>
            <span class="summary-item"><strong>{{ cnnForm.lr }}</strong><small>LR</small></span>
            <span class="summary-item"><strong>{{ cnnForm.weightDecay }}</strong><small>WD</small></span>
          </div>
        </div>

        <div class="model-hint">
          <strong>下次输出模型</strong>
          <span class="muted">{{ cnnOutputPreview }}</span>
          <span v-if="latestCnnModel" class="model-metric">
            最新 CNN：{{ latestCnnModel.name }}，best_acc：{{ numberText(latestCnnModel.best_acc) }}
          </span>
          <span v-else class="muted">暂未检测到 CNN 模型，训练完成后会出现在这里。</span>
        </div>
      </div>

      <div class="panel training-card featured">
        <div class="training-head">
          <div>
            <span class="eyebrow">训练路线 2</span>
            <strong>Triplet 度量学习模型</strong>
            <p class="muted">用 ResNet/CNN 骨干训练 Triplet Loss，让同类图片更近、异类图片更远；可从已训练 CNN 继续，也可从零训练。</p>
          </div>
          <span class="model-badge">Triplet</span>
        </div>

        <el-form label-position="top" class="compact-form">
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <span class="param-label">Epoch <ParamInfo :info="parameterInfos.epochs" @open="openParamDialog('epochs')" /></span>
              </template>
              <el-input-number v-model="tripletForm.epochs" :min="1" :max="500" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Batch Size <ParamInfo :info="parameterInfos.batchSize" @open="openParamDialog('batchSize')" /></span>
              </template>
              <el-input-number v-model="tripletForm.batchSize" :min="16" :max="1024" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">学习率 <ParamInfo :info="parameterInfos.lr" @open="openParamDialog('lr')" /></span>
              </template>
              <el-input-number v-model="tripletForm.lr" :min="0.0001" :max="1" :step="0.001" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Eval K <ParamInfo :info="parameterInfos.evalK" @open="openParamDialog('evalK')" /></span>
              </template>
              <el-input-number v-model="tripletForm.evalK" :min="1" :max="100" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Margin <ParamInfo :info="parameterInfos.margin" @open="openParamDialog('margin')" /></span>
              </template>
              <el-input-number v-model="tripletForm.margin" :min="0.05" :max="2" :step="0.05" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">Triplet 权重 <ParamInfo :info="parameterInfos.tripletWeight" @open="openParamDialog('tripletWeight')" /></span>
              </template>
              <el-input-number v-model="tripletForm.tripletWeight" :min="0" :max="10" :step="0.1" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="param-label">权重衰减 WD <ParamInfo :info="parameterInfos.weightDecay" @open="openParamDialog('weightDecay')" /></span>
              </template>
              <el-input-number v-model="tripletForm.weightDecay" :min="0" :max="0.1" :step="0.0001" controls-position="right" />
            </el-form-item>
          </div>
          <el-form-item>
            <template #label>
              <span class="param-label">预训练 CNN <ParamInfo :info="parameterInfos.pretrained" @open="openParamDialog('pretrained')" /></span>
            </template>
            <el-select
              v-model="tripletForm.pretrained"
              filterable
              placeholder="选择 CNN checkpoint"
            >
              <el-option label="不使用预训练，从零训练" :value="NO_PRETRAINED" />
              <el-option
                v-for="model in cnnModels"
                :key="model.relative_path || model.path"
                :label="modelLabel(model)"
                :value="model.relative_path || model.path"
              />
            </el-select>
          </el-form-item>
          <div class="form-row">
            <div class="checkbox-with-info">
              <el-checkbox v-model="tripletForm.amp">使用 AMP 混合精度</el-checkbox>
              <ParamInfo :info="parameterInfos.amp" @open="openParamDialog('amp')" />
            </div>
            <el-button type="primary" :loading="starting" @click="trainTriplet">开始训练 Triplet</el-button>
          </div>
        </el-form>

        <div class="training-summary">
          <span>当前配置</span>
          <div>
            <span class="summary-item"><strong>{{ tripletForm.epochs }}</strong><small>Epoch</small></span>
            <span class="summary-item"><strong>{{ tripletForm.margin }}</strong><small>Margin</small></span>
            <span class="summary-item"><strong>{{ tripletForm.evalK }}</strong><small>Eval K</small></span>
            <span class="summary-item"><strong>{{ tripletForm.tripletWeight }}</strong><small>Triplet</small></span>
          </div>
        </div>

        <div class="model-hint">
          <strong>下次输出模型</strong>
          <span class="muted">{{ tripletOutputPreview }}</span>
          <span v-if="latestTripletModel" class="model-metric">
            最新 Triplet：{{ latestTripletModel.name }}，best_acc：{{ numberText(latestTripletModel.best_acc) }}，P@K：{{ numberText(latestTripletModel.best_p_at_k) }}
          </span>
          <span v-else class="muted">建议先完成 CNN 训练，再训练 Triplet 模型。</span>
        </div>
      </div>
    </section>

    <section class="after-index-grid">
      <div class="panel index-card">
        <div>
          <span class="eyebrow">训练后操作 1</span>
          <strong>CNN 索引</strong>
          <p class="muted">选择一个 CNN 分类模型 checkpoint，重建 deep_cnn 索引。</p>
        </div>
        <el-form label-position="top" class="compact-form">
          <el-form-item label="选择 CNN .pt">
            <el-select v-model="indexForm.cnnModel" filterable placeholder="选择 CNN 模型" :disabled="cnnModels.length === 0">
              <el-option
                v-for="model in cnnModels"
                :key="model.relative_path || model.path"
                :label="modelLabel(model)"
                :value="model.relative_path || model.path"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="index-actions">
          <el-button type="primary" :loading="starting" :disabled="cnnModels.length === 0" @click="buildCnnIndex">
            重建 CNN 索引
          </el-button>
          <el-button :loading="starting" @click="evaluateFeature('deep_cnn')">评估 CNN</el-button>
        </div>
      </div>

      <div class="panel index-card featured">
        <div>
          <span class="eyebrow">训练后操作 2</span>
          <strong>Triplet 索引</strong>
          <p class="muted">选择一个 Triplet 度量学习 checkpoint，重建 deep_triplet 索引。</p>
        </div>
        <el-form label-position="top" class="compact-form">
          <el-form-item label="选择 Triplet .pt">
            <el-select
              v-model="indexForm.tripletModel"
              filterable
              placeholder="选择 Triplet 模型"
              :disabled="tripletModels.length === 0"
            >
              <el-option
                v-for="model in tripletModels"
                :key="model.relative_path || model.path"
                :label="modelLabel(model)"
                :value="model.relative_path || model.path"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="index-actions">
          <el-button type="primary" :loading="starting" :disabled="tripletModels.length === 0" @click="buildTripletIndex">
            重建 Triplet 索引
          </el-button>
          <el-button :loading="starting" @click="evaluateFeature('deep_triplet')">评估 Triplet</el-button>
        </div>
      </div>
    </section>

    <section class="panel task-panel">
      <div class="task-header">
        <strong>任务中心</strong>
        <div class="task-actions">
          <el-button size="small" @click="loadTasks">刷新</el-button>
          <el-button size="small" :disabled="!hasFinishedTasks" @click="clearTasks('finished')">清空已结束</el-button>
          <el-button size="small" type="danger" plain :disabled="tasks.length === 0" @click="clearTasks('all')">
            清空全部
          </el-button>
        </div>
      </div>
      <el-table :data="tasks" height="260" @row-click="selectTask">
        <el-table-column prop="name" label="任务" min-width="220" />
        <el-table-column prop="kind" label="类型" width="110" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="280">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress :percentage="taskPercent(row)" :status="progressStatus(row.status)" :stroke-width="8" />
              <span v-if="row.progress?.epoch" class="muted">
                epoch {{ row.progress.epoch }}/{{ row.progress.total_epochs || '?' }}，
                val_acc {{ Number(row.progress.val_acc || 0).toFixed(4) }}
                <template v-if="row.progress?.p_at_k">，P@K {{ Number(row.progress.p_at_k).toFixed(4) }}</template>
              </span>
              <span v-else-if="row.result?.map" class="muted">
                mAP {{ Number(row.result.map).toFixed(4) }}，P@K {{ Number(row.result.p_at_k).toFixed(4) }}
              </span>
              <span v-else-if="row.progress?.current" class="muted">
                {{ row.progress.label || '处理' }} {{ row.progress.current }}/{{ row.progress.total || '?' }}
              </span>
              <span v-else class="muted">{{ progressHint(row.status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" plain :disabled="!canCancel(row)" @click.stop="cancelTask(row)">
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="log-view">
        <div class="log-title">
          <strong>{{ selectedTask?.name || '未选择任务' }}</strong>
          <span v-if="selectedTask" class="muted">{{ selectedTask.id }}</span>
        </div>
        <pre>{{ selectedLogs }}</pre>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import ParamInfo from '../components/ParamInfo.vue'
import TaskOverlay from '../components/TaskOverlay.vue'
import {
  cancelPipelineTask,
  clearPipelineTasks,
  fetchDeepModels,
  fetchPipelineTasks,
  startMetricTraining,
  startModelTraining,
  startPipelineEvaluate,
  startPipelineIndex
} from '../api/cbir'

const DATASET = 'cifar10'
const CIFAR10_SRC = '../data/raw/cifar-10-batches-py'
const MODELS_PREFIX = '../data/models'
const DEFAULT_CNN_CHECKPOINT = `${MODELS_PREFIX}/cifar_resnet18.pt`
const NO_PRETRAINED = '__none__'
const parameterInfos = {
  epochs: {
    title: 'Epoch 训练轮数',
    short: '模型完整看完训练集的次数。',
    impact: '调大通常更充分，但训练更久，也可能过拟合。',
    meaning: '一个 epoch 表示模型把 50000 张 CIFAR-10 训练图片完整学习一遍。Epoch 越多，模型有更多机会修正参数。',
    effect: '太小会欠拟合，模型还没学充分；适当增大通常会提高准确率；过大时训练集准确率继续升高，但测试集效果可能不再提升甚至下降。',
    suggestion: 'CNN 可以保持 80 左右；Triplet 可以先用 40 左右观察 P@K，再根据验证结果加减。',
    details: ['Epoch 控制训练充分程度。', '不是越大越好，需要结合验证集准确率和检索指标判断。']
  },
  batchSize: {
    title: 'Batch Size 批大小',
    short: '每次送进 GPU 训练的图片数量。',
    impact: '调大更快更稳但更吃显存；调小省显存但波动更大。',
    meaning: '训练不会一次处理全部图片，而是分成很多小批次。Batch Size 就是每个小批次包含多少张图片。',
    effect: 'Batch Size 增大时 GPU 利用率通常更高，但显存占用也会上升；Batch Size 过小时梯度噪声更大，训练曲线可能更抖。',
    suggestion: 'RTX 4060 上 CIFAR-10 用 128 是比较稳妥的默认值；显存不足可以降到 64。',
    details: ['Batch Size 是训练效率和显存占用之间的折中。', '它不会直接决定最终效果，但会影响训练稳定性。']
  },
  lr: {
    title: '学习率 Learning Rate',
    short: '每次更新模型参数时迈多大一步。',
    impact: '太大容易震荡发散；太小训练慢、收敛不足。',
    meaning: '学习率控制优化器修改网络权重的幅度，是训练中最敏感的参数之一。',
    effect: '学习率大时前期下降快，但可能越过最优点；学习率小时更稳，但需要更多 epoch 才能达到好结果。',
    suggestion: '分类 CNN 默认 0.1 配合 SGD 和余弦退火；Triplet 默认 0.01 更保守，因为度量学习对特征空间扰动更敏感。',
    details: ['学习率决定模型学习速度。', '本项目使用 CosineAnnealingLR，让学习率在训练中逐渐降低。']
  },
  workers: {
    title: 'Workers 数据加载线程数',
    short: '后台并行读取和预处理数据的进程数。',
    impact: '调大可减少等待数据的时间，但过大可能占用 CPU。',
    meaning: '训练时 GPU 负责计算，CPU 同时负责读图片、增强和组成 batch。Workers 控制这些数据准备工作的并行数量。',
    effect: 'Workers 太小可能让 GPU 等数据；Workers 太大可能让系统变卡，尤其是 Windows 环境下。',
    suggestion: '当前默认 2 比较稳。如果训练时 GPU 利用率低，可以尝试 4；如果电脑明显卡顿，可以设为 0 或 1。',
    details: ['Workers 主要影响训练速度，不直接改变模型数学目标。', '它属于工程性能参数。']
  },
  weightDecay: {
    title: '权重衰减 WD',
    short: '限制模型权重过大，减少过拟合。',
    impact: '适当增大更抗过拟合；过大可能压制模型学习能力。',
    meaning: 'WD 是 weight decay 的缩写，本质是一种正则化，会惩罚过大的网络权重，让模型不要只死记训练集。',
    effect: 'WD 太小时模型可能过拟合；WD 太大时模型被限制得太强，训练准确率也可能上不去。',
    suggestion: 'CIFAR-10 的 ResNet 常用 0.0005，本项目默认也采用这个值。',
    details: ['WD 用来提升泛化能力。', '它和 Epoch 配合看：训练越久，正则化越重要。']
  },
  amp: {
    title: 'AMP 混合精度',
    short: '用较低精度加速 GPU 训练。',
    impact: '通常更快更省显存；极少数情况下数值稳定性略受影响。',
    meaning: 'AMP 会让部分计算使用 float16，关键部分仍保留合适精度，从而在支持 CUDA 的显卡上提升训练效率。',
    effect: '开启后训练速度通常更快、显存占用更低；关闭后更保守，但训练更慢。',
    suggestion: 'RTX 4060 支持 CUDA，建议开启。若训练出现异常 loss，再尝试关闭排查。',
    details: ['AMP 是工程加速策略，不改变模型结构。', '本项目会自动判断 CUDA 可用性。']
  },
  evalK: {
    title: 'Eval K 检索评估邻居数',
    short: '评估 Triplet 特征时看前 K 个近邻。',
    impact: 'K 小更看重最前排结果；K 大更看重整体排序稳定性。',
    meaning: 'Triplet 模型不仅看分类准确率，还会看同类图片在特征空间里是否靠近。Eval K 就是计算 P@K 时取前多少个检索结果。',
    effect: 'K 越小，指标更严格地反映最靠前结果；K 越大，指标更接近整体同类聚集情况。',
    suggestion: '本项目检索页默认 Top-K 附近常用 12，所以 Eval K 默认 12，便于训练评估和页面检索口径一致。',
    details: ['Eval K 对应检索任务中的 P@K。', '它不直接参与反向传播，主要用于选择最佳 checkpoint。']
  },
  margin: {
    title: 'Margin 三元组间隔',
    short: '要求正样本比负样本至少近多少。',
    impact: '调大约束更强；过大可能训练困难。',
    meaning: 'Triplet Loss 使用 anchor、positive、negative 三张图片，希望 anchor 到 positive 的距离比到 negative 的距离更小，并至少小 margin 这么多。',
    effect: 'Margin 太小，模型区分类别的压力不够；Margin 太大，很多样本都难以满足，训练可能不稳定。',
    suggestion: '默认 0.2 是比较温和的间隔，适合先跑通 CIFAR-10 的度量学习。',
    details: ['Margin 控制类内紧凑和类间分离的要求强度。', '它是 Triplet Loss 的核心超参数。']
  },
  tripletWeight: {
    title: 'Triplet 权重',
    short: 'Triplet Loss 在总损失中的占比。',
    impact: '调大更强调检索特征；过大可能影响分类稳定性。',
    meaning: '本项目 Triplet 训练同时使用交叉熵分类损失和 Triplet Loss。Triplet 权重控制度量学习目标在总损失里有多重要。',
    effect: '权重大时，模型更努力拉近同类、推远异类；权重过大时分类目标可能被削弱，训练更难稳定。',
    suggestion: '默认 1.0 表示保留较强的检索优化目标；如果分类准确率下降明显，可以适当降低。',
    details: ['这是分类目标和检索目标之间的平衡旋钮。', '它直接影响最终特征空间的形状。']
  },
  pretrained: {
    title: '预训练 CNN',
    short: 'Triplet 训练是否从已有 CNN 权重开始。',
    impact: '使用预训练通常更稳更快；从零训练更纯粹但更难。',
    meaning: 'Triplet 模型的骨干仍是 ResNet/CNN。可以先用分类任务学到基础图像特征，再用 Triplet Loss 微调特征空间。',
    effect: '选择已有 CNN 时，模型起点更好，收敛更快；选择从零训练时，所有权重随机初始化，可能需要更多 epoch。',
    suggestion: '建议选择已经训练好的 CNN checkpoint，更容易得到稳定结果。',
    details: ['Triplet 不一定必须依赖 CNN 分类训练，但通常用它作为更好的初始化。', '这体现了“先分类学习语义，再度量学习优化检索”的思路。']
  }
}

const cnnForm = reactive({
  epochs: 80,
  batchSize: 128,
  lr: 0.1,
  weightDecay: 0.0005,
  workers: 2,
  amp: true
})
const tripletForm = reactive({
  epochs: 40,
  batchSize: 128,
  lr: 0.01,
  weightDecay: 0.0005,
  workers: 2,
  amp: true,
  margin: 0.2,
  tripletWeight: 1,
  ceWeight: 0.5,
  evalK: 12,
  pretrained: ''
})
const indexForm = reactive({
  cnnModel: '',
  tripletModel: ''
})

const tasks = ref([])
const selectedTask = ref(null)
const deepModels = ref([])
const starting = ref(false)
const taskOverlayVisible = ref(false)
const overlayTaskId = ref('')
const paramDialogVisible = ref(false)
const activeParamKey = ref('')
let timer = null

const selectedLogs = computed(() => {
  if (!selectedTask.value) return '选择一个任务后显示日志。'
  return selectedTask.value.logs?.join('\n') || '暂无日志。'
})
const hasFinishedTasks = computed(() =>
  tasks.value.some((task) => ['succeeded', 'failed', 'cancelled'].includes(task.status))
)
const cnnModels = computed(() => deepModels.value.filter((model) => !model.training_objective))
const tripletModels = computed(() => deepModels.value.filter((model) => Boolean(model.training_objective)))
const latestCnnModel = computed(() => cnnModels.value[0] || null)
const latestTripletModel = computed(() => tripletModels.value[0] || null)
const cnnOutputPreview = computed(() => displayModelPath(makeOutputPath('cnn', cnnForm)))
const tripletOutputPreview = computed(() => displayModelPath(makeOutputPath('triplet', tripletForm)))
const overlayTask = computed(() => tasks.value.find((task) => task.id === overlayTaskId.value) || selectedTask.value)
const activeParam = computed(() => parameterInfos[activeParamKey.value] || null)

function baseTrainPayload(form) {
  return {
    dataset: DATASET,
    src: CIFAR10_SRC,
    label_level: 'fine',
    epochs: Number(form.epochs),
    batch_size: Number(form.batchSize),
    lr: Number(form.lr),
    weight_decay: Number(form.weightDecay),
    workers: Number(form.workers),
    amp: Boolean(form.amp)
  }
}

function openParamDialog(key) {
  activeParamKey.value = key
  paramDialogVisible.value = true
}

function formatParam(value) {
  return String(Number(value)).replace('-', 'm').replace('.', 'p').replace(/[^a-zA-Z0-9]/g, '')
}

function modelFileName(kind, form) {
  const parts = [
    DATASET,
    kind,
    `e${Number(form.epochs)}`,
    `bs${Number(form.batchSize)}`,
    `lr${formatParam(form.lr)}`,
    `wd${formatParam(form.weightDecay)}`
  ]
  if (kind === 'triplet') {
    parts.push(
      `m${formatParam(form.margin)}`,
      `tw${formatParam(form.tripletWeight)}`,
      `ce${formatParam(form.ceWeight)}`,
      `k${Number(form.evalK)}`
    )
  }
  return `${parts.join('_')}.pt`
}

function makeOutputPath(kind, form) {
  return `${MODELS_PREFIX}/${modelFileName(kind, form)}`
}

function displayModelPath(path) {
  return path.replace(/^\.\.\//, '')
}

function modelLabel(model) {
  const metrics = []
  if (model.best_acc !== null && model.best_acc !== undefined) {
    metrics.push(`acc ${numberText(model.best_acc)}`)
  }
  if (model.best_p_at_k !== null && model.best_p_at_k !== undefined) {
    metrics.push(`P@K ${numberText(model.best_p_at_k)}`)
  }
  return metrics.length > 0 ? `${model.name}（${metrics.join(' / ')}）` : model.name
}

function modelValue(model) {
  return model?.relative_path || model?.path || ''
}

function hasModelValue(models, value) {
  return Boolean(value) && models.some((model) => modelValue(model) === value)
}

function syncModelSelections() {
  const firstCnn = modelValue(cnnModels.value[0])
  const firstTriplet = modelValue(tripletModels.value[0])
  if (!hasModelValue(cnnModels.value, indexForm.cnnModel)) {
    indexForm.cnnModel = firstCnn
  }
  if (!hasModelValue(tripletModels.value, indexForm.tripletModel)) {
    indexForm.tripletModel = firstTriplet
  }
  if (tripletForm.pretrained !== NO_PRETRAINED && !hasModelValue(cnnModels.value, tripletForm.pretrained)) {
    tripletForm.pretrained = firstCnn
  }
}

async function runStarter(action) {
  starting.value = true
  try {
    const task = await action()
    selectedTask.value = task
    overlayTaskId.value = task.id
    taskOverlayVisible.value = true
    ElMessage.success('任务已启动')
    await loadTasks()
  } finally {
    starting.value = false
  }
}

async function trainCnn() {
  const output = makeOutputPath('cnn', cnnForm)
  await runStarter(() => startModelTraining({ ...baseTrainPayload(cnnForm), output }))
}

async function trainTriplet() {
  const pretrained =
    tripletForm.pretrained === NO_PRETRAINED
      ? ''
      : tripletForm.pretrained || latestCnnModel.value?.relative_path || latestCnnModel.value?.path || DEFAULT_CNN_CHECKPOINT
  if (!latestCnnModel.value && !tripletForm.pretrained) {
    try {
      await ElMessageBox.confirm(
        '当前没有检测到 CNN 基础模型。Triplet 可以继续训练，但建议先训练 CNN，再进行度量学习。',
        '继续训练 Triplet？',
        {
          confirmButtonText: '继续训练',
          cancelButtonText: '先不训练',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  const output = makeOutputPath('triplet', tripletForm)
  await runStarter(() =>
    startMetricTraining({
      ...baseTrainPayload(tripletForm),
      margin: Number(tripletForm.margin),
      triplet_weight: Number(tripletForm.tripletWeight),
      ce_weight: Number(tripletForm.ceWeight),
      eval_k: Number(tripletForm.evalK),
      pretrained,
      output
    })
  )
}

async function buildCnnIndex() {
  if (!indexForm.cnnModel) {
    ElMessage.warning('请先选择一个 CNN 模型')
    return
  }
  await runStarter(() =>
    startPipelineIndex({
      dataset: DATASET,
      features: ['deep_cnn'],
      cnn_model: indexForm.cnnModel
    })
  )
}

async function buildTripletIndex() {
  if (!indexForm.tripletModel) {
    ElMessage.warning('请先选择一个 Triplet 模型')
    return
  }
  await runStarter(() =>
    startPipelineIndex({
      dataset: DATASET,
      features: ['deep_triplet'],
      triplet_model: indexForm.tripletModel
    })
  )
}

async function evaluateFeature(feature) {
  await runStarter(() =>
    startPipelineEvaluate({
      dataset: DATASET,
      feature,
      metric: 'cosine',
      k: 12,
      sample: 100
    })
  )
}

async function loadDeepModels() {
  const result = await fetchDeepModels()
  deepModels.value = result.models || []
  syncModelSelections()
}

function numberText(value) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toFixed(4)
}

async function loadTasks() {
  tasks.value = await fetchPipelineTasks()
  if (selectedTask.value) {
    selectedTask.value = tasks.value.find((task) => task.id === selectedTask.value.id) || tasks.value[0] || null
  } else {
    selectedTask.value = tasks.value[0] || null
  }
  await loadDeepModels()
}

async function clearTasks(mode) {
  if (mode === 'all') {
    try {
      await ElMessageBox.confirm('这会取消正在运行的任务，并清空任务中心记录。', '清空全部任务', {
        confirmButtonText: '清空',
        cancelButtonText: '返回',
        type: 'warning'
      })
    } catch {
      return
    }
  }
  tasks.value = await clearPipelineTasks(mode)
  selectedTask.value = tasks.value.find((task) => task.id === selectedTask.value?.id) || tasks.value[0] || null
  ElMessage.success(mode === 'all' ? '任务中心已清空' : '已清空结束任务')
}

function selectTask(row) {
  selectedTask.value = row
}

function statusType(status) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'cancelled') return 'info'
  if (status === 'cancelling') return 'warning'
  if (status === 'running') return 'warning'
  return 'info'
}

function statusText(status) {
  return {
    queued: '排队中',
    running: '运行中',
    cancelling: '取消中',
    cancelled: '已取消',
    succeeded: '已完成',
    failed: '失败'
  }[status] || status
}

function taskPercent(task) {
  if (task.status === 'succeeded') return 100
  if (task.status === 'failed' || task.status === 'cancelled') return 100
  if (task.progress?.percent !== undefined) return Math.min(99, Math.round(Number(task.progress.percent) || 0))
  if (task.progress?.epoch && task.progress?.total_epochs) {
    return Math.min(99, Math.round((task.progress.epoch / task.progress.total_epochs) * 100))
  }
  if (task.status === 'running' || task.status === 'cancelling') return 15
  return 0
}

function progressStatus(status) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'warning'
  return ''
}

function progressHint(status) {
  if (status === 'running') return '运行中，等待日志'
  if (status === 'cancelling') return '正在取消'
  if (status === 'cancelled') return '已取消'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  return '等待开始'
}

function canCancel(task) {
  return task.status === 'queued' || task.status === 'running'
}

async function cancelTask(task) {
  try {
    await cancelPipelineTask(task.id)
    ElMessage.success('已发送取消请求')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '取消失败')
  } finally {
    await loadTasks()
  }
}

async function cancelOverlayTask() {
  const task = overlayTask.value
  if (!task) return
  await cancelTask(task)
}

onMounted(async () => {
  await loadTasks()
  timer = window.setInterval(loadTasks, 2000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.model-page {
  display: grid;
  gap: 18px;
}

.header-panel,
.task-header,
.form-row,
.log-title,
.training-head,
.after-train-panel,
.index-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-panel p,
.dataset-panel p,
.training-head p,
.after-train-panel p {
  margin: 6px 0 0;
}

.dataset-lock {
  display: grid;
  justify-items: end;
  gap: 4px;
  min-width: 220px;
  padding: 10px 14px;
  color: #ffffff;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.18);
}

.dataset-lock span {
  font-size: 18px;
  font-weight: 900;
}

.dataset-lock small {
  opacity: 0.9;
}

.dataset-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 0.8fr) auto;
  gap: 16px;
  align-items: center;
}

.eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
}

.dataset-panel h3 {
  margin: 4px 0 0;
  font-size: 22px;
}

.source-path {
  display: grid;
  gap: 6px;
}

.source-path span {
  color: var(--text-muted);
  font-size: 13px;
}

.source-path code {
  display: block;
  padding: 10px 12px;
  border: 1px solid var(--code-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 5%);
  word-break: break-all;
}

.dataset-facts {
  display: grid;
  gap: 8px;
}

.dataset-facts span {
  min-width: 118px;
  padding: 8px 10px;
  text-align: center;
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent), transparent 68%);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 6%);
  font-weight: 800;
}

.training-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.after-index-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.training-card,
.index-card,
.task-panel {
  display: grid;
  gap: 14px;
  align-content: start;
  min-width: 0;
  overflow: hidden;
}

.training-card.featured {
  border-color: color-mix(in srgb, var(--accent-2), transparent 55%);
}

.index-card.featured {
  border-color: color-mix(in srgb, var(--accent-2), transparent 55%);
}

.training-head {
  align-items: flex-start;
}

.training-head > div {
  min-width: 0;
}

.training-head strong {
  display: block;
  margin-top: 4px;
  font-size: 22px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.training-head p {
  overflow-wrap: anywhere;
}

.model-badge {
  flex: 0 0 auto;
  padding: 8px 12px;
  color: #ffffff;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  font-weight: 900;
}

.compact-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.param-label,
.checkbox-with-info {
  display: inline-flex;
  align-items: center;
  min-width: 0;
}

.checkbox-with-info {
  gap: 2px;
}

.compact-form :deep(.el-form-item__content),
.compact-form :deep(.el-input),
.compact-form :deep(.el-input__wrapper),
.compact-form :deep(.el-select__wrapper) {
  min-width: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.form-grid :deep(.el-form-item) {
  min-width: 0;
}

.form-grid :deep(.el-input-number) {
  width: 100%;
  max-width: 100%;
}

.form-grid :deep(.el-input-number .el-input) {
  width: 100%;
  max-width: 100%;
}

.compact-form :deep(.el-select) {
  width: 100%;
  max-width: 100%;
}

.model-hint {
  display: grid;
  gap: 4px;
  min-width: 0;
  min-height: 96px;
  padding: 10px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 4%);
}

.training-summary {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid color-mix(in srgb, var(--accent-2), transparent 70%);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent), transparent 92%), transparent),
    var(--control-bg);
}

.training-summary > span {
  color: var(--text-muted);
  font-size: 13px;
}

.training-summary > div {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.training-summary .summary-item {
  display: grid;
  gap: 3px;
  justify-items: center;
  min-width: 0;
}

.training-summary .summary-item strong,
.training-summary .summary-item small {
  display: block;
  min-width: 0;
  text-align: center;
}

.training-summary .summary-item strong {
  color: var(--text-main);
  font-size: 17px;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.training-summary .summary-item small {
  color: var(--text-muted);
  font-size: 12px;
}

.model-metric {
  color: var(--accent-2);
  font-weight: 800;
  overflow-wrap: anywhere;
}

.model-hint .muted {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.after-train-panel {
  align-items: flex-start;
}

.index-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-cell {
  display: grid;
  gap: 4px;
}

.log-view {
  overflow: hidden;
  color: #d1d5db;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #111827;
}

.log-title {
  padding: 10px 12px;
  color: #f9fafb;
  border-bottom: 1px solid #374151;
}

.log-view pre {
  min-height: 180px;
  max-height: 320px;
  margin: 0;
  overflow: auto;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
}

.param-detail {
  display: grid;
  gap: 14px;
}

.param-summary {
  margin: 0;
  padding: 12px 14px;
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent), transparent 72%);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 7%);
  font-weight: 800;
  line-height: 1.55;
}

.param-detail section {
  display: grid;
  gap: 6px;
}

.param-detail section strong {
  color: var(--text-main);
  font-size: 15px;
}

.param-detail p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.65;
}

.param-detail ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-muted);
  line-height: 1.65;
}

.param-detail li + li {
  margin-top: 4px;
}

@media (max-width: 1080px) {
  .dataset-panel,
  .training-grid,
  .after-index-grid {
    grid-template-columns: 1fr;
  }

  .dataset-facts {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .header-panel,
  .task-header,
  .form-row,
  .after-train-panel,
  .index-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .dataset-lock {
    justify-items: start;
  }

  .form-grid,
  .dataset-facts {
    grid-template-columns: 1fr;
  }
}
</style>
