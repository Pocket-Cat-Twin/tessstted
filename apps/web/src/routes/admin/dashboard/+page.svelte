<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';
  import { api } from '$lib/api/client-simple';

  const stats: any = {
    orders: { total: 0, processing: 0, completed: 0 },
    users: { total: 0, active: 0, subscribed: 0 },
    revenue: { total: 0, thisMonth: 0 },
    system: { uptime: '0s', status: 'unknown' }
  };
  let recentOrders: any[] = [];
  let systemHealth: any = null;
  let loading = true;
  let error = '';

  interface QuickAction {
    label: string;
    description: string;
    icon: string;
    href: string;
    color: string;
  }

  const quickActions: QuickAction[] = [
    {
      label: 'Управление заказами',
      description: 'Просмотр и обработка заказов',
      icon: '📦',
      href: '/admin/orders',
      color: 'bg-blue-500'
    },
    {
      label: 'Пользователи',
      description: 'Управление пользователями и подписками',
      icon: '👥',
      href: '/admin/users',
      color: 'bg-green-500'
    },
    {
      label: 'Мониторинг системы',
      description: 'Статистика и производительность',
      icon: '📈',
      href: '/admin/monitoring',
      color: 'bg-purple-500'
    },
    {
      label: 'Настройки системы',
      description: 'Конфигурация и резервное копирование',
      icon: '⚙️',
      href: '/admin/system',
      color: 'bg-orange-500'
    }
  ];

  onMount(async () => {
    await loadDashboardData();
  });

  async function loadDashboardData() {
    loading = true;
    error = '';

    try {
      // Load multiple data sources in parallel
      const [ordersResponse, healthResponse] = await Promise.all([
        api.getAdminOrders(),
        fetchSystemHealth()
      ]);

      // Process orders data
      if (ordersResponse.success) {
        const orders = ordersResponse.data?.orders || [];
        stats.orders.total = orders.length;
        stats.orders.processing = orders.filter(o => ['created', 'processing', 'checking'].includes(o.status)).length;
        stats.orders.completed = orders.filter(o => o.status === 'delivered').length;
        stats.revenue.total = orders.reduce((sum, o) => sum + (o.totalRuble || 0), 0);
        
        // Get recent orders (last 10)
        recentOrders = orders
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          .slice(0, 10);
      }

      // Process system health
      if (healthResponse.success) {
        systemHealth = healthResponse.data;
        stats.system = {
          uptime: formatUptime(healthResponse.data.uptime || 0),
          status: healthResponse.data.status || 'unknown'
        };
      }

    } catch (err) {
      error = 'Ошибка загрузки данных';
      console.error('Dashboard loading error:', err);
    } finally {
      loading = false;
    }
  }

  async function fetchSystemHealth() {
    try {
      const response = await fetch('/api/v1/monitoring/health');
      return await response.json();
    } catch (error) {
      return { success: false, error };
    }
  }

  function formatUptime(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  }

  function getStatusColor(status: string) {
    switch (status.toLowerCase()) {
      case 'created': return 'bg-blue-100 text-blue-800';
      case 'processing': return 'bg-yellow-100 text-yellow-800';
      case 'checking': return 'bg-orange-100 text-orange-800';
      case 'paid': return 'bg-green-100 text-green-800';
      case 'shipped': return 'bg-purple-100 text-purple-800';
      case 'delivered': return 'bg-green-100 text-green-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }
</script>

<svelte:head>
  <title>Dashboard - Admin Panel</title>
</svelte:head>

<div class="p-6 space-y-6">
  <!-- Page Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p class="text-gray-600 mt-1">Обзор системы и ключевые метрики</p>
    </div>
    <div class="flex items-center space-x-2">
      <Button variant="outline" size="sm" on:click={loadDashboardData}>
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
    <Card variant="bordered" className="p-6 text-center">
      <div class="text-red-600 mb-4">
        <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Ошибка загрузки</h3>
      <p class="text-gray-600 mb-4">{error}</p>
      <Button variant="primary" on:click={loadDashboardData}>
        Попробовать снова
      </Button>
    </Card>
  {:else}
    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Orders Card -->
      <Card variant="shadow" className="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center">
              <span class="text-2xl">📦</span>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Заказы</p>
            <p class="text-2xl font-semibold text-gray-900">{stats.orders.total}</p>
            <p class="text-xs text-gray-500 mt-1">
              {stats.orders.processing} в обработке
            </p>
          </div>
        </div>
      </Card>

      <!-- Revenue Card -->
      <Card variant="shadow" className="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center">
              <span class="text-2xl">💰</span>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Выручка</p>
            <p class="text-2xl font-semibold text-gray-900">
              {stats.revenue.total.toLocaleString('ru-RU')} ₽
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Общий объем
            </p>
          </div>
        </div>
      </Card>

      <!-- System Status Card -->
      <Card variant="shadow" className="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class={`w-12 h-12 rounded-xl flex items-center justify-center ${
              systemHealth?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
            }`}>
              <span class="text-2xl">
                {systemHealth?.status === 'healthy' ? '✅' : '❌'}
              </span>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Система</p>
            <p class="text-2xl font-semibold text-gray-900">
              {systemHealth?.status === 'healthy' ? 'Работает' : 'Проблемы'}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Время работы: {stats.system.uptime}
            </p>
          </div>
        </div>
      </Card>

      <!-- Performance Card -->
      <Card variant="shadow" className="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center">
              <span class="text-2xl">⚡</span>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Производительность</p>
            <p class="text-2xl font-semibold text-gray-900">
              {systemHealth?.performance?.averageResponseTime || 0}ms
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Среднее время ответа
            </p>
          </div>
        </div>
      </Card>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {#each quickActions as action}
        <Card variant="bordered" className="p-6 hover:shadow-lg transition-shadow cursor-pointer">
          <a href={action.href} class="block">
            <div class="flex items-center mb-4">
              <div class={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center mr-3`}>
                <span class="text-xl">{action.icon}</span>
              </div>
              <h3 class="text-lg font-semibold text-gray-900">{action.label}</h3>
            </div>
            <p class="text-gray-600 text-sm">{action.description}</p>
          </a>
        </Card>
      {/each}
    </div>

    <!-- Recent Orders and System Info -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Recent Orders -->
      <Card variant="shadow" className="overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Последние заказы</h2>
            <Button variant="outline" size="sm" href="/admin/orders">
              Все заказы →
            </Button>
          </div>
        </div>
        
        <div class="divide-y divide-gray-200">
          {#each recentOrders.slice(0, 5) as order}
            <div class="px-6 py-4 hover:bg-gray-50">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-2">
                    <p class="text-sm font-medium text-gray-900">
                      #{order.nomerok}
                    </p>
                    <Badge variant="secondary" className={getStatusColor(order.status)}>
                      {order.status}
                    </Badge>
                  </div>
                  <p class="text-sm text-gray-500 mt-1">
                    {order.customerName}
                  </p>
                </div>
                <div class="text-right">
                  <p class="text-sm font-medium text-gray-900">
                    {order.totalRuble?.toLocaleString('ru-RU')} ₽
                  </p>
                  <p class="text-xs text-gray-500">
                    {new Date(order.createdAt).toLocaleDateString('ru-RU')}
                  </p>
                </div>
              </div>
            </div>
          {/each}
          
          {#if recentOrders.length === 0}
            <div class="px-6 py-8 text-center">
              <p class="text-gray-500">Нет заказов</p>
            </div>
          {/if}
        </div>
      </Card>

      <!-- System Information -->
      <Card variant="shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Информация о системе</h2>
        </div>
        
        <div class="p-6 space-y-4">
          {#if systemHealth}
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Статус</dt>
                <dd class={`text-sm font-semibold ${
                  systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {systemHealth.status === 'healthy' ? 'Работает нормально' : 'Есть проблемы'}
                </dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">Время работы</dt>
                <dd class="text-sm text-gray-900">
                  {formatUptime(systemHealth.uptime || 0)}
                </dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">Память</dt>
                <dd class="text-sm text-gray-900">
                  {systemHealth.memory?.used || 0} MB / {systemHealth.memory?.total || 0} MB
                </dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">База данных</dt>
                <dd class={`text-sm font-semibold ${
                  systemHealth.database?.status === 'connected' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {systemHealth.database?.status === 'connected' ? 'Подключена' : 'Отключена'}
                </dd>
              </div>
            </div>

            <div class="pt-4 border-t border-gray-200">
              <div class="flex justify-between items-center">
                <span class="text-sm font-medium text-gray-500">
                  Производительность
                </span>
                <Button variant="outline" size="sm" href="/admin/monitoring">
                  Подробнее →
                </Button>
              </div>
              <div class="mt-2 space-y-2">
                <div class="flex justify-between text-sm">
                  <span class="text-gray-600">Среднее время ответа:</span>
                  <span class="font-medium">{systemHealth.performance?.averageResponseTime || 0}ms</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-600">Процент ошибок:</span>
                  <span class="font-medium">{systemHealth.performance?.errorRate || 0}%</span>
                </div>
              </div>
            </div>
          {:else}
            <div class="text-center py-6">
              <Spinner size="sm" />
              <p class="text-sm text-gray-500 mt-2">Загрузка информации о системе...</p>
            </div>
          {/if}
        </div>
      </Card>
    </div>
  {/if}
</div>