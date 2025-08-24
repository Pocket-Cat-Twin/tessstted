<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';

  let metrics: any = null;
  let healthData: any = null;
  let loading = true;
  let error = '';
  let refreshInterval: any = null;

  onMount(() => {
    loadMonitoringData();
    
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(loadMonitoringData, 30000);
    
    // Cleanup on component destroy
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });

  async function loadMonitoringData() {
    try {
      const [metricsResponse, healthResponse] = await Promise.all([
        fetch('/api/v1/monitoring/metrics'),
        fetch('/api/v1/monitoring/health')
      ]);

      const [metricsData, healthResponseData] = await Promise.all([
        metricsResponse.json(),
        healthResponse.json()
      ]);

      if (metricsData.success) {
        metrics = metricsData.data;
      }

      if (healthResponseData.success) {
        healthData = healthResponseData.data;
      }

      loading = false;
      error = '';
    } catch (err) {
      error = 'Ошибка загрузки данных мониторинга';
      loading = false;
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}д ${hours}ч ${minutes}м`;
    if (hours > 0) return `${hours}ч ${minutes}м`;
    return `${minutes}м`;
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  }
</script>

<svelte:head>
  <title>Мониторинг - Admin Panel</title>
</svelte:head>

<div class="p-6 space-y-6">
  <!-- Page Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Мониторинг системы</h1>
      <p class="text-gray-600 mt-1">Отслеживание производительности и состояния системы</p>
    </div>
    <div class="flex items-center space-x-2">
      <Button variant="outline" size="sm" on:click={loadMonitoringData}>
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Обновить
      </Button>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center items-center py-12">
      <Spinner size="lg" />
    </div>
  {:else if error}
    <Card variant="bordered" class="p-6 text-center">
      <div class="text-red-600 mb-4">
        <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Ошибка загрузки</h3>
      <p class="text-gray-600 mb-4">{error}</p>
      <Button variant="primary" on:click={loadMonitoringData}>
        Попробовать снова
      </Button>
    </Card>
  {:else}
    <!-- System Health Overview -->
    {#if healthData}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="shadow" class="p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900">Общее состояние</h3>
            <Badge variant={getStatusBadge(healthData.status)}>
              {healthData.status === 'healthy' ? 'Работает' : 'Проблемы'}
            </Badge>
          </div>
          <div class="space-y-3">
            <div class="flex justify-between">
              <span class="text-gray-600">Время работы:</span>
              <span class="font-medium">{formatUptime(healthData.uptime || 0)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">База данных:</span>
              <Badge variant={healthData.database?.status === 'connected' ? 'success' : 'danger'}>
                {healthData.database?.status === 'connected' ? 'Подключена' : 'Отключена'}
              </Badge>
            </div>
          </div>
        </Card>

        <Card variant="shadow" class="p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Память</h3>
          <div class="space-y-3">
            <div class="flex justify-between">
              <span class="text-gray-600">Используется:</span>
              <span class="font-medium">{formatBytes((healthData.memory?.used || 0) * 1024 * 1024)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Всего:</span>
              <span class="font-medium">{formatBytes((healthData.memory?.total || 0) * 1024 * 1024)}</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div 
                class="bg-blue-600 h-2 rounded-full" 
                style="width: {healthData.memory?.used && healthData.memory?.total ? (healthData.memory.used / healthData.memory.total * 100) : 0}%"
              ></div>
            </div>
          </div>
        </Card>

        <Card variant="shadow" class="p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Производительность</h3>
          <div class="space-y-3">
            <div class="flex justify-between">
              <span class="text-gray-600">Ср. время ответа:</span>
              <span class="font-medium">{healthData.performance?.averageResponseTime || 0}ms</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">Ошибки:</span>
              <span class="font-medium">{healthData.performance?.errorRate || 0}%</span>
            </div>
          </div>
        </Card>
      </div>
    {/if}

    <!-- Detailed Metrics -->
    {#if metrics}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Request Metrics -->
        <Card variant="shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900">Запросы</h3>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Всего запросов</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.requests?.total || 0}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Среднее время</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.performance?.averageResponseTime || 0}ms</dd>
              </div>
            </div>
            
            <div>
              <h4 class="text-sm font-medium text-gray-700 mb-2">По статус-кодам:</h4>
              <div class="space-y-1">
                {#each Object.entries(metrics.requests?.byStatus || {}) as [status, count]}
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">{status}xx:</span>
                    <span class="font-medium">{count}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </Card>

        <!-- Error Metrics -->
        <Card variant="shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900">Ошибки</h3>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Всего ошибок</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.errors?.total || 0}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Процент ошибок</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.errors?.errorRate || 0}%</dd>
              </div>
            </div>
            
            {#if metrics.errors?.recent && metrics.errors.recent.length > 0}
              <div>
                <h4 class="text-sm font-medium text-gray-700 mb-2">Последние ошибки:</h4>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                  {#each metrics.errors.recent.slice(0, 5) as error}
                    <div class="text-xs bg-red-50 p-2 rounded border-l-2 border-red-200">
                      <div class="font-medium text-red-800">{error.path}</div>
                      <div class="text-red-600 mt-1">{error.error}</div>
                      <div class="text-red-500 text-right">
                        {new Date(error.timestamp).toLocaleTimeString('ru-RU')}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </Card>

        <!-- Database Metrics -->
        <Card variant="shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900">База данных</h3>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Запросы</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.database?.queries || 0}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Медленные запросы</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.database?.slowQueries || 0}</dd>
              </div>
            </div>
            
            <div class="flex justify-between">
              <span class="text-sm text-gray-600">Процент медленных:</span>
              <span class="text-sm font-medium">{metrics.database?.slowQueryPercentage || 0}%</span>
            </div>
          </div>
        </Card>

        <!-- Business Metrics -->
        <Card variant="shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900">Бизнес-метрики</h3>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Заказы</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.business?.orders || 0}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Подписки</dt>
                <dd class="text-2xl font-semibold text-gray-900">{metrics.business?.subscriptions || 0}</dd>
              </div>
            </div>
            
            <div>
              <dt class="text-sm font-medium text-gray-500">Выручка</dt>
              <dd class="text-2xl font-semibold text-gray-900">
                {(metrics.business?.revenue || 0).toLocaleString('ru-RU')} ₽
              </dd>
            </div>

            <div class="space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Входы:</span>
                <span class="font-medium">{metrics.auth?.logins || 0}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Неудачные входы:</span>
                <span class="font-medium">{metrics.auth?.failures || 0}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Регистрации:</span>
                <span class="font-medium">{metrics.auth?.registrations || 0}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Top Endpoints -->
      {#if metrics.requests?.byPath}
        <Card variant="shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-gray-900">Популярные endpoints</h3>
          </div>
          <div class="p-6">
            <div class="space-y-2">
              {#each Object.entries(metrics.requests.byPath).slice(0, 10) as [path, count]}
                <div class="flex justify-between items-center">
                  <span class="text-sm text-gray-600 font-mono">{path}</span>
                  <div class="flex items-center space-x-2">
                    <span class="text-sm font-medium">{count}</span>
                    <div class="w-20 bg-gray-200 rounded-full h-2">
                      <div 
                        class="bg-blue-600 h-2 rounded-full" 
                        style="width: {(Number(count) / Math.max(...Object.values(metrics.requests.byPath).map(Number)) * 100)}%"
                      ></div>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </Card>
      {/if}
    {/if}
  {/if}
</div>