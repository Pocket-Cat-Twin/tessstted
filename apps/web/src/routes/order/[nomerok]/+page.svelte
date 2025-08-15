<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { ordersStore } from '$lib/stores/orders';
  import Button from '$components/ui/Button.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import { formatCurrency, formatDate } from '@yuyu/shared';
  import type { Order } from '@yuyu/shared';

  $: nomerok = $page.params.nomerok;
  
  let loading = true;
  let error = '';
  let order: Order | null = null;

  onMount(async () => {
    if (nomerok) {
      await loadOrder();
    }
  });

  async function loadOrder() {
    loading = true;
    error = '';
    
    const result = await ordersStore.getByNumber(nomerok);
    loading = false;

    if (result.success) {
      order = result.order;
      error = '';
    } else {
      error = result.message || 'Заказ не найден';
      order = null;
    }
  }

  function getStatusColor(status: string) {
    switch (status.toLowerCase()) {
      case 'новый':
      case 'new':
        return 'gray';
      case 'в обработке':
      case 'processing':
        return 'blue';
      case 'оплачен':
      case 'paid':
        return 'green';
      case 'отправлен':
      case 'shipped':
        return 'purple';
      case 'доставлен':
      case 'delivered':
        return 'green';
      case 'отменен':
      case 'cancelled':
        return 'red';
      default:
        return 'gray';
    }
  }

  function getStatusText(status: string) {
    switch (status.toLowerCase()) {
      case 'new': return 'Новый';
      case 'processing': return 'В обработке';
      case 'paid': return 'Оплачен';
      case 'shipped': return 'Отправлен';
      case 'delivered': return 'Доставлен';
      case 'cancelled': return 'Отменен';
      default: return status;
    }
  }
</script>

<svelte:head>
  <title>Заказ {nomerok} - YuYu Lolita Shopping</title>
  <meta name="description" content="Информация о заказе {nomerok}" />
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm">
    <div class="container-custom py-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Заказ #{nomerok}
          </h1>
          <p class="text-lg text-gray-600">
            Подробная информация о вашем заказе
          </p>
        </div>
        
        <div class="flex items-center space-x-4">
          <Button
            variant="outline"
            on:click={() => window.history.back()}
          >
            Назад
          </Button>
          <Button
            variant="outline"
            on:click={loadOrder}
            {loading}
            disabled={loading}
          >
            {loading ? 'Обновление...' : 'Обновить'}
          </Button>
        </div>
      </div>
    </div>
  </div>

  <div class="container-custom py-8">
    <!-- Loading State -->
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="flex items-center space-x-3">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
          <span class="text-gray-600">Загрузка информации о заказе...</span>
        </div>
      </div>
    {/if}

    <!-- Error State -->
    {#if error && !loading}
      <div class="max-w-2xl mx-auto">
        <div class="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg text-center">
          <div class="flex items-center justify-center space-x-2 mb-4">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-lg font-medium">Заказ не найден</span>
          </div>
          <p class="mb-4">{error}</p>
          <div class="flex items-center justify-center space-x-3">
            <Button variant="outline" href="/track">
              Поиск заказа
            </Button>
            <Button variant="primary" href="/create">
              Создать новый заказ
            </Button>
          </div>
        </div>
      </div>
    {/if}

    <!-- Order Details -->
    {#if order && !loading}
      <div class="max-w-4xl mx-auto space-y-6">
        <!-- Order Status & Summary -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-semibold text-gray-900">
              Статус заказа
            </h2>
            <Badge color={getStatusColor(order.status)} size="lg">
              {getStatusText(order.status)}
            </Badge>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="text-center p-4 bg-gray-50 rounded-lg">
              <div class="text-2xl font-bold text-primary-600 mb-1">
                {formatCurrency(order.totalCost, 'RUB')}
              </div>
              <div class="text-sm text-gray-600">Общая стоимость</div>
            </div>
            
            <div class="text-center p-4 bg-gray-50 rounded-lg">
              <div class="text-2xl font-bold text-gray-900 mb-1">
                {formatDate(order.createdAt)}
              </div>
              <div class="text-sm text-gray-600">Дата создания</div>
            </div>
            
            <div class="text-center p-4 bg-gray-50 rounded-lg">
              <div class="text-2xl font-bold text-gray-900 mb-1">
                {order.deliveryMethod}
              </div>
              <div class="text-sm text-gray-600">Способ доставки</div>
            </div>
          </div>
        </div>

        <!-- Customer Information -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
            <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Информация о заказчике
          </h2>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 class="font-medium text-gray-900 mb-3">Контактные данные</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Имя:</span>
                  <span class="font-medium">{order.customerName}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Телефон:</span>
                  <span class="font-medium">{order.customerPhone}</span>
                </div>
                {#if order.customerEmail}
                  <div class="flex justify-between">
                    <span class="text-gray-600">Email:</span>
                    <span class="font-medium">{order.customerEmail}</span>
                  </div>
                {/if}
              </div>
            </div>

            <div>
              <h3 class="font-medium text-gray-900 mb-3">Доставка и оплата</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Способ доставки:</span>
                  <span class="font-medium">{order.deliveryMethod}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Способ оплаты:</span>
                  <span class="font-medium">{order.paymentMethod}</span>
                </div>
              </div>
            </div>
          </div>

          {#if order.deliveryAddress}
            <div class="mt-6 pt-6 border-t border-gray-200">
              <h3 class="font-medium text-gray-900 mb-2">Адрес доставки</h3>
              <p class="text-sm text-gray-600 p-3 bg-gray-50 rounded-lg">{order.deliveryAddress}</p>
            </div>
          {/if}
        </div>

        <!-- Order Goods -->
        {#if order.goods && order.goods.length > 0}
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
              Товары в заказе ({order.goods.length})
            </h2>
            
            <div class="space-y-4">
              {#each order.goods as good, index}
                <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <h3 class="font-medium text-gray-900 mb-2 flex items-center">
                        <span class="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-xs font-bold mr-2">
                          {index + 1}
                        </span>
                        {good.name}
                      </h3>
                      
                      {#if good.link}
                        <a 
                          href={good.link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          class="text-sm text-primary-600 hover:text-primary-700 underline mb-3 inline-flex items-center"
                        >
                          Ссылка на товар
                          <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </a>
                      {/if}
                      
                      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span class="text-gray-600 block">Количество</span>
                          <span class="font-medium">{good.quantity} шт.</span>
                        </div>
                        <div>
                          <span class="text-gray-600 block">Цена за шт.</span>
                          <span class="font-medium">¥{good.priceYuan.toFixed(2)}</span>
                        </div>
                        <div>
                          <span class="text-gray-600 block">Сумма</span>
                          <span class="font-medium">¥{(good.quantity * good.priceYuan).toFixed(2)}</span>
                        </div>
                        <div>
                          <span class="text-gray-600 block">Статус</span>
                          <Badge color="blue" size="sm">В заказе</Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Status History -->
        {#if order.statusHistory && order.statusHistory.length > 0}
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              История заказа
            </h2>
            
            <div class="space-y-4">
              {#each order.statusHistory as historyItem, index}
                <div class="flex items-start space-x-4 py-4 {index !== order.statusHistory.length - 1 ? 'border-b border-gray-100' : ''}">
                  <div class="flex-shrink-0 pt-1">
                    <div class="w-4 h-4 rounded-full bg-primary-500 relative">
                      {#if index !== order.statusHistory.length - 1}
                        <div class="absolute top-4 left-1/2 transform -translate-x-1/2 w-0.5 h-8 bg-gray-200"></div>
                      {/if}
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                      <div>
                        <p class="font-medium text-gray-900">
                          {getStatusText(historyItem.status)}
                        </p>
                        {#if historyItem.comment}
                          <p class="text-sm text-gray-600 mt-1">{historyItem.comment}</p>
                        {/if}
                      </div>
                      <div class="text-sm text-gray-500 ml-4">
                        {formatDate(historyItem.createdAt)}
                      </div>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Actions -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">Действия</h2>
          
          <div class="flex flex-wrap gap-4">
            <Button variant="outline" href="/track">
              Отследить другой заказ
            </Button>
            <Button variant="outline" href="/create">
              Создать новый заказ
            </Button>
            <Button 
              variant="outline"
              on:click={() => window.print()}
            >
              Распечатать
            </Button>
          </div>
        </div>

        <!-- Help Section -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 class="font-medium text-blue-900 mb-2">Нужна помощь с заказом?</h3>
              <p class="text-sm text-blue-700 mb-3">
                Если у вас возникли вопросы по заказу или вам нужна помощь, свяжитесь с нами:
              </p>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm text-blue-700">
                <div>📱 +7 (999) 123-45-67</div>
                <div>📧 support@yuyu-lolita.ru</div>
                <div>💬 @yuyu_support</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

