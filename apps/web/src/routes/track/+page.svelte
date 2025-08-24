<script lang="ts">
  // import { onMount } from 'svelte';
  import { ordersStore } from '$lib/stores/orders';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';
  import { formatCurrency, formatDate, type Order } from '@lolita-fashion/shared';

  let orderNumber = '';
  let loading = false;
  let error = '';
  let order: Order | null = null;
  let searched = false;

  async function handleSearch() {
    if (!orderNumber.trim()) {
      error = 'Введите номер заказа';
      return;
    }

    loading = true;
    error = '';
    order = null;

    const result = await ordersStore.lookup(orderNumber.trim());
    loading = false;
    searched = true;

    if (result.success) {
      order = result.order;
      error = '';
    } else {
      error = result.message || 'Заказ не найден';
      order = null;
    }
  }

  function getStatusVariant(status: string) {
    switch (status.toLowerCase()) {
      case 'новый':
      case 'new':
      case 'created':
        return 'secondary';
      case 'в обработке':
      case 'processing':
      case 'checking':
        return 'info';
      case 'оплачен':
      case 'paid':
        return 'success';
      case 'отправлен':
      case 'shipped':
        return 'primary';
      case 'доставлен':
      case 'delivered':
        return 'success';
      case 'отменен':
      case 'cancelled':
        return 'danger';
      default:
        return 'secondary';
    }
  }

  function getStatusText(status: string) {
    switch (status.toLowerCase()) {
      case 'created': return 'Новый';
      case 'processing': return 'В обработке';
      case 'checking': return 'Проверка';
      case 'paid': return 'Оплачен';
      case 'shipped': return 'Отправлен';
      case 'delivered': return 'Доставлен';
      case 'cancelled': return 'Отменен';
      default: return status;
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }
</script>

<svelte:head>
  <title>Отследить заказ - YuYu Lolita Shopping</title>
  <meta name="description" content="Отследите статус вашего заказа по номеру заказа" />
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm">
    <div class="container-custom py-8">
      <div class="text-center">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          Отследить заказ
        </h1>
        <p class="text-lg text-gray-600 max-w-2xl mx-auto">
          Введите номер заказа, чтобы узнать его текущий статус
        </p>
      </div>
    </div>
  </div>

  <div class="container-custom py-8">
    <div class="max-w-2xl mx-auto">
      <!-- Search Form -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
        <div class="space-y-4">
          <Input
            label="Номер заказа"
            placeholder="Введите номер заказа (например: YY240704001)"
            bind:value={orderNumber}
            disabled={loading}
            on:keydown={handleKeyPress}
          />
          
          <div class="flex justify-center">
            <Button
              variant="primary"
              size="lg"
              {loading}
              disabled={loading || !orderNumber.trim()}
              on:click={handleSearch}
            >
              {loading ? 'Поиск...' : 'Найти заказ'}
            </Button>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      {#if error}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-8 text-center">
          <div class="flex items-center justify-center space-x-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      {/if}

      <!-- Order Not Found -->
      {#if searched && !order && !error}
        <div class="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg mb-8 text-center">
          <div class="flex items-center justify-center space-x-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span>Заказ с номером "{orderNumber}" не найден</span>
          </div>
        </div>
      {/if}

      <!-- Order Details -->
      {#if order}
        <div class="space-y-6">
          <!-- Order Info -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-semibold text-gray-900">
                Заказ #{order.nomerok}
              </h2>
              <Badge variant={getStatusVariant(order.status)} size="lg">
                {getStatusText(order.status)}
              </Badge>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 class="font-medium text-gray-900 mb-3">Информация о заказе</h3>
                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-600">Дата создания:</span>
                    <span class="font-medium">{formatDate(order.createdAt)}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">Общая стоимость:</span>
                    <span class="font-medium text-primary-600">{formatCurrency(order.totalRuble, 'RUB')}</span>
                  </div>
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

              <div>
                <h3 class="font-medium text-gray-900 mb-3">Контактная информация</h3>
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
            </div>

            {#if order.deliveryAddress}
              <div class="mt-6 pt-6 border-t border-gray-200">
                <h3 class="font-medium text-gray-900 mb-2">Адрес доставки</h3>
                <p class="text-sm text-gray-600">{order.deliveryAddress}</p>
              </div>
            {/if}
          </div>

          <!-- Order Goods -->
          {#if order.goods && order.goods.length > 0}
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 class="text-xl font-semibold text-gray-900 mb-6">Товары в заказе</h2>
              
              <div class="space-y-4">
                {#each order.goods as good}
                  <div class="border border-gray-200 rounded-lg p-4">
                    <div class="flex items-start justify-between">
                      <div class="flex-1">
                        <h3 class="font-medium text-gray-900 mb-2">{good.name}</h3>
                        {#if good.link}
                          <a 
                            href={good.link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            class="text-sm text-primary-600 hover:text-primary-700 underline mb-2 block"
                          >
                            Ссылка на товар ↗
                          </a>
                        {/if}
                        <div class="flex items-center space-x-4 text-sm text-gray-600">
                          <span>Количество: {good.quantity}</span>
                          <span>Цена: ¥{good.priceYuan.toFixed(2)}</span>
                          <span class="font-medium text-gray-900">
                            Итого: ¥{(good.quantity * good.priceYuan).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Status History -->
          <!-- Note: Status history will be implemented when backend provides this data -->
          <!-- 
          {#if order.statusHistory && order.statusHistory.length > 0}
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 class="text-xl font-semibold text-gray-900 mb-6">История заказа</h2>
              
              <div class="space-y-4">
                {#each order.statusHistory as historyItem}
                  <div class="flex items-center space-x-4 py-3 border-b border-gray-100 last:border-b-0">
                    <div class="flex-shrink-0">
                      <div class="w-3 h-3 rounded-full bg-primary-500"></div>
                    </div>
                    <div class="flex-1">
                      <div class="flex items-center justify-between">
                        <span class="font-medium text-gray-900">
                          {getStatusText(historyItem.status)}
                        </span>
                        <span class="text-sm text-gray-500">
                          {formatDate(historyItem.createdAt)}
                        </span>
                      </div>
                      {#if historyItem.comment}
                        <p class="text-sm text-gray-600 mt-1">{historyItem.comment}</p>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
          -->
        </div>
      {/if}

      <!-- Help Section -->
      <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <div class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 class="font-medium text-blue-900 mb-2">Нужна помощь?</h3>
            <p class="text-sm text-blue-700 mb-3">
              Если у вас возникли вопросы по заказу или вы не можете его найти, свяжитесь с нами:
            </p>
            <div class="space-y-1 text-sm text-blue-700">
              <p>📱 Телефон: +7 (999) 123-45-67</p>
              <p>📧 Email: support@yuyu-lolita.ru</p>
              <p>💬 Telegram: @yuyu_support</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>