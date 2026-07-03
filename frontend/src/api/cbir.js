import client from './client'

export async function fetchDatasets() {
  const response = await client.get('/datasets')
  return response.data
}

export async function searchByFile({
  dataset,
  file,
  feature = 'color_hist',
  metric = 'intersection',
  weights = null,
  topK = 12
}) {
  const form = new FormData()
  form.append('dataset', dataset)
  form.append('feature', feature)
  form.append('metric', metric)
  form.append('top_k', String(topK))
  if (weights) {
    form.append('weights', JSON.stringify(weights))
  }
  form.append('file', file)
  const response = await client.post('/search', form)
  return response.data
}

export async function searchByText({ dataset, text, topK = 12 }) {
  const form = new FormData()
  form.append('dataset', dataset)
  form.append('text', text)
  form.append('top_k', String(topK))
  const response = await client.post('/search/text', form)
  return response.data
}

export async function fetchImages({ dataset, page = 1, size = 24, category = '' }) {
  const response = await client.get(`/datasets/${dataset}/images`, {
    params: { page, size, category: category || undefined }
  })
  return response.data
}

export async function fetchCategories(dataset) {
  const response = await client.get(`/datasets/${dataset}/categories`)
  return response.data
}

export async function uploadImage({ dataset, file, category = '' }) {
  const form = new FormData()
  form.append('dataset', dataset)
  if (category) {
    form.append('category', category)
  }
  form.append('file', file)
  const response = await client.post('/images', form)
  return response.data
}

export async function deleteImage(imageId) {
  await client.delete(`/images/${imageId}`)
}

export async function fetchHistogram({ dataset, imageId, type = 'hsv' }) {
  const response = await client.get('/histogram', {
    params: { dataset, image_id: imageId, type }
  })
  return response.data
}

export async function evaluateFeature({ dataset, feature, metric, k = 12, sample = 100 }) {
  const response = await client.get('/evaluate', {
    params: { dataset, feature, metric, k, sample }
  })
  return response.data
}

export async function buildIndex({ dataset, features }) {
  const response = await client.post('/index/build', { dataset, features })
  return response.data
}

export async function fetchPipelineTasks() {
  const response = await client.get('/pipeline/tasks')
  return response.data
}

export async function fetchPipelineTask(taskId) {
  const response = await client.get(`/pipeline/tasks/${taskId}`)
  return response.data
}

export async function cancelPipelineTask(taskId) {
  const response = await client.post(`/pipeline/tasks/${taskId}/cancel`, null, { skipGlobalError: true })
  return response.data
}

export async function clearPipelineTasks(mode = 'finished') {
  const response = await client.post('/pipeline/tasks/clear', null, {
    params: { mode }
  })
  return response.data
}

export async function uploadDatasetArchive({ file, extract = true }) {
  const form = new FormData()
  form.append('file', file)
  const response = await client.post('/pipeline/upload', form, {
    params: { extract }
  })
  return response.data
}

export async function startDatasetDownload({ url, filename = '' }) {
  const response = await client.post('/pipeline/download', null, {
    params: { url, filename: filename || undefined }
  })
  return response.data
}

export async function startDatasetPrepare(payload) {
  const response = await client.post('/pipeline/prepare', payload)
  return response.data
}

export async function startModelTraining(payload) {
  const response = await client.post('/pipeline/train', payload)
  return response.data
}

export async function startMetricTraining(payload) {
  const response = await client.post('/pipeline/train-metric', payload)
  return response.data
}

export async function startPipelineIndex(payload) {
  const response = await client.post('/pipeline/index', payload)
  return response.data
}

export async function startPipelineEvaluate(payload) {
  const response = await client.post('/pipeline/evaluate', payload)
  return response.data
}

export async function fetchVideos({ page = 1, size = 12 } = {}) {
  const response = await client.get('/videos', {
    params: { page, size }
  })
  return response.data
}

export async function uploadVideo({ file, intervalSeconds = 2, maxKeyframes = 60 }) {
  const form = new FormData()
  form.append('file', file)
  form.append('interval_seconds', String(intervalSeconds))
  form.append('max_keyframes', String(maxKeyframes))
  const response = await client.post('/videos', form)
  return response.data
}

export async function deleteVideo(videoId) {
  await client.delete(`/videos/${videoId}`)
}

export async function importLocalVideos({ intervalSeconds = 2, maxKeyframes = 60 }) {
  const form = new FormData()
  form.append('interval_seconds', String(intervalSeconds))
  form.append('max_keyframes', String(maxKeyframes))
  const response = await client.post('/videos/import-local', form)
  return response.data
}

export async function buildVideoIndex({ feature = 'deep' }) {
  const form = new FormData()
  form.append('feature', feature)
  const response = await client.post('/videos/index', form)
  return response.data
}

export async function searchVideosByImage({ file, feature = 'deep', metric = 'cosine', topK = 6 }) {
  const form = new FormData()
  form.append('file', file)
  form.append('feature', feature)
  form.append('metric', metric)
  form.append('top_k', String(topK))
  const response = await client.post('/videos/search', form)
  return response.data
}
