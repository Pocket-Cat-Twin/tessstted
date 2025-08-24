<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth';
  import Button from '$lib/components/ui/Button.svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { api } from '$lib/api/client-simple';

  let orders: any[] = [];
  let loading = true;
  let error = '';

  $: user = $authStore.user;

  // Check if user is admin
  $: if (user && user.role !== 'admin') {
    goto('/');
  }

  onMount(async () => {
    await loadOrders();
  });

  async function loadOrders() {
    loading = true;
    error = '';

    try {
      const response = await api.getAdminOrders();
      
      if (response.success) {
        orders = response.data?.orders || [];
      } else {
        error = response.message || 'Ошибка загрузки заказов';
      }
    } catch (err) {
      error = 'Ошибка подключения к серверу';
    } finally {
      loading = false;
    }
  }

  async function updateOrderStatus(orderId: string, newStatus: string) {
    try {
      const response = await api.updateOrderStatus(orderId, newStatus);
      
      if (response.success) {
        // Update order in local array
        const orderIndex = orders.findIndex(o => o.id === orderId);
        if (orderIndex !== -1) {
          orders[orderIndex].status = newStatus;
          orders = [...orders]; // Trigger reactivity
        }
      } else {
        alert('Ошибка обновления статуса: ' + (response.message || 'Неизвестная ошибка'));
      }
    } catch (err) {
      alert('Ошибка подключения к серверу');
    }
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

  function getStatusText(status: string) {
    switch (status.toLowerCase()) {
      case 'created': return 'Создан';
      case 'processing': return 'В обработке';
      case 'checking': return 'Проверяется';
      case 'paid': return 'Оплачен';
      case 'shipped': return 'Отправлен';
      case 'delivered': return 'Доставлен';
      case 'cancelled': return 'Отменён';
      default: return status;
    }
  }

  function handleStatusChange(orderId: string, event: Event) {
    const select = event.target as HTMLSelectElement;
    if (select?.value) {
      updateOrderStatus(orderId, select.value);
    }
  }
</script>

<svelte:head>
  <title>Админ панель - YuYu Lolita</title>
  <meta name="description" content="Панель администратора для управления заказами YuYu Lolita" />
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center py-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Админ панель</h1>
          <p class="text-gray-600 mt-1">Управление заказами и системой</p>
        </div>
        
        <div class="flex items-center space-x-4">
          <Button variant="outline" on:click={() => goto('/')}>
            Вернуться на сайт
          </Button>
          
          {#if user}
            <div class="flex items-center space-x-2">
              <div class="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
                <span class="text-white font-medium text-sm">
                  {user.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <span class="text-gray-700 font-medium">{user.name}</span>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <Card variant="shadow" class="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Всего заказов</p>
            <p class="text-2xl font-semibold text-gray-900">{orders.length}</p>
          </div>
        </div>
      </Card>

      <Card variant="shadow" class="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">В обработке</p>
            <p class="text-2xl font-semibold text-gray-900">
              {orders.filter(o => ['created', 'processing', 'checking'].includes(o.status)).length}
            </p>
          </div>
        </div>
      </Card>

      <Card variant="shadow" class="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Завершённые</p>
            <p class="text-2xl font-semibold text-gray-900">
              {orders.filter(o => o.status === 'delivered').length}
            </p>
          </div>
        </div>
      </Card>

      <Card variant="shadow" class="p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-primary-500 rounded-md flex items-center justify-center">
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Общая сумма</p>
            <p class="text-2xl font-semibold text-gray-900">
              {orders.reduce((sum, o) => sum + (o.totalRuble || 0), 0).toLocaleString('ru-RU')} ₽
            </p>
          </div>
        </div>
      </Card>
    </div>

    <!-- Orders Table -->
    <Card variant="shadow" class="overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">Заказы</h2>
          <div class="flex items-center space-x-3">
            <Button variant="outline" size="sm" on:click={loadOrders}>
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Обновить
            </Button>
          </div>
        </div>
      </div>

      {#if loading}
        <div class="flex justify-center items-center py-12">
          <Spinner size="large" />
        </div>
      {:else if error}
        <div class="px-6 py-12 text-center">
          <div class="text-red-600 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">Ошибка загрузки</h3>
          <p class="text-gray-600 mb-4">{error}</p>
          <Button variant="primary" on:click={loadOrders}>
            Попробовать снова
          </Button>
        </div>
      {:else if orders.length === 0}
        <div class="px-6 py-12 text-center">
          <div class="text-gray-400 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">Пока нет заказов</h3>
          <p class="text-gray-600">Заказы будут появляться здесь по мере их создания</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Номер заказа
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Клиент
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Статус
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Сумма
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Дата
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each orders as order}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">{order.nomerok}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">{order.customerName}</div>
                    <div class="text-sm text-gray-500">{order.customerEmail}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {getStatusColor(order.status)}">
                      {getStatusText(order.status)}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {order.totalRuble?.toLocaleString('ru-RU')} ₽
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(order.createdAt).toLocaleDateString('ru-RU')}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex items-center space-x-2">
                      <select 
                        value={order.status}
                        on:change={(e) => handleStatusChange(order.id, e)}
                        class="text-xs border border-gray-300 rounded px-2 py-1"
                      >
                        <option value="created">Создан</option>
                        <option value="processing">В обработке</option>
                        <option value="checking">Проверяется</option>
                        <option value="paid">Оплачен</option>
                        <option value="shipped">Отправлен</option>
                        <option value="delivered">Доставлен</option>
                        <option value="cancelled">Отменён</option>
                      </select>
                      
                      <Button 
                        variant="outline" 
                        size="sm"
                        on:click={() => goto(`/order/${order.nomerok}`)}
                      >
                        Просмотреть
                      </Button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </Card>
  </div>
</div>