<script lang="ts">
  import { onMount } from 'svelte';
  import { authStore } from '$lib/stores/auth';
  import { goto } from '$app/navigation';
  import Button from '$lib/components/ui/Button.svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';

  interface Order {
    id: string;
    nomerok: string;
    customerName: string;
    customerPhone: string;
    customerEmail: string;
    deliveryAddress: string;
    deliveryMethod: string;
    paymentMethod: string;
    status: string;
    goods: Array<{
      name: string;
      priceYuan: number;
      quantity: number;
      color: string;
      size: string;
    }>;
    totalRuble: number;
    createdAt: string;
    updatedAt: string;
  }

  let orders: Order[] = [];
  let loading = true;
  let error = '';

  // Status color mapping
  const statusColors: Record<string, 'success' | 'primary' | 'secondary' | 'danger' | 'warning' | 'info'> = {
    'CREATED': 'secondary',
    'CONFIRMED': 'info',
    'PAID': 'success',
    'SHIPPED': 'primary',
    'DELIVERED': 'success',
    'CANCELLED': 'danger'
  };

  const statusLabels: Record<string, string> = {
    'CREATED': 'Создан',
    'CONFIRMED': 'Подтвержден',
    'PAID': 'Оплачен',
    'SHIPPED': 'Отправлен',
    'DELIVERED': 'Доставлен',
    'CANCELLED': 'Отменен'
  };

  onMount(async () => {
    // Check if user is authenticated
    if (!$authStore.user) {
      goto('/login');
      return;
    }
    
    await loadOrders();
  });

  async function loadOrders() {
    loading = true;
    error = '';
    
    try {
      const response = await fetch('http://127.0.0.1:3001/orders', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch orders');
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Map user orders to expected format
        orders = data.orders.map((order: any) => ({
          id: order.id,
          nomerok: order.id,
          customerName: $authStore.user?.name || 'Пользователь',
          customerPhone: $authStore.user?.phone || '',
          customerEmail: $authStore.user?.email || '',
          deliveryAddress: 'Адрес не указан',
          deliveryMethod: 'Обычная доставка',
          paymentMethod: 'Не указан',
          status: order.status.toUpperCase(),
          goods: [{
            name: order.goods,
            priceYuan: order.totalPriceCny,
            quantity: 1,
            color: 'Не указан',
            size: 'Не указан'
          }],
          totalRuble: Math.round(order.finalPrice * 15), // Convert CNY to RUB
          createdAt: order.createdAt,
          updatedAt: order.updatedAt
        }));
      } else {
        error = 'Не удалось загрузить заказы';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Ошибка загрузки заказов';
    } finally {
      loading = false;
    }
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function formatPrice(price: number) {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB'
    }).format(price);
  }

  function goToOrderDetails(nomerok: string) {
    goto(`/order/${nomerok}`);
  }
</script>

<svelte:head>
  <title>Мои заказы - YuYu Lolita</title>
  <meta name="description" content="Список ваших заказов в YuYu Lolita с актуальными статусами и возможностью отслеживания" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 to-purple-50">
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Мои <span class="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600">заказы</span>
      </h1>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto">
        Отслеживайте статус ваших заказов и получайте актуальную информацию о доставке
      </p>
    </div>

    {#if loading}
      <!-- Loading state -->
      <div class="flex justify-center items-center py-12">
        <Spinner size="large" />
      </div>
    {:else if error}
      <!-- Error state -->
      <div class="text-center py-12">
        <div class="bg-red-50 border border-red-200 rounded-lg p-8 max-w-md mx-auto">
          <div class="text-red-600 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-red-800 mb-2">Ошибка загрузки</h3>
          <p class="text-red-600 mb-4">{error}</p>
          <Button variant="secondary" on:click={loadOrders}>
            Попробовать снова
          </Button>
        </div>
      </div>
    {:else if orders.length === 0}
      <!-- Empty state -->
      <div class="text-center py-12">
        <div class="text-gray-400 mb-4">
          <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
          </svg>
        </div>
        <h3 class="text-xl font-medium text-gray-900 mb-2">У вас пока нет заказов</h3>
        <p class="text-gray-600 mb-6">Начните покупки и отслеживайте свои заказы здесь</p>
        <Button variant="primary" on:click={() => goto('/create')}>
          Создать заказ
        </Button>
      </div>
    {:else}
      <!-- Orders List -->
      <div class="max-w-6xl mx-auto">
        <div class="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
          {#each orders as order}
            <Card class="overflow-hidden transition-all duration-300 hover:shadow-lg">
              <div class="p-6">
                <!-- Order header -->
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">
                      Заказ #{order.nomerok}
                    </h3>
                    <p class="text-sm text-gray-500">
                      {formatDate(order.createdAt)}
                    </p>
                  </div>
                  <Badge variant={statusColors[order.status] || 'secondary'}>
                    {statusLabels[order.status] || order.status}
                  </Badge>
                </div>

                <!-- Order details -->
                <div class="space-y-3 mb-6">
                  <!-- Goods -->
                  <div>
                    <h4 class="text-sm font-medium text-gray-700 mb-2">Товары:</h4>
                    <div class="space-y-1">
                      {#each order.goods as good}
                        <div class="text-sm text-gray-600 flex justify-between">
                          <span>
                            {good.name} 
                            <span class="text-gray-500">({good.color}, {good.size})</span>
                          </span>
                          <span>×{good.quantity}</span>
                        </div>
                      {/each}
                    </div>
                  </div>

                  <!-- Delivery info -->
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                    <div>
                      <span class="font-medium text-gray-700">Доставка:</span>
                      <span class="text-gray-600">{order.deliveryMethod}</span>
                    </div>
                    <div>
                      <span class="font-medium text-gray-700">Оплата:</span>
                      <span class="text-gray-600">{order.paymentMethod}</span>
                    </div>
                  </div>

                  <!-- Total -->
                  <div class="border-t pt-3">
                    <div class="flex justify-between items-center">
                      <span class="text-lg font-semibold text-gray-900">Итого:</span>
                      <span class="text-xl font-bold text-pink-600">
                        {formatPrice(order.totalRuble)}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex gap-3">
                  <Button 
                    variant="primary" 
                    size="sm" 
                    on:click={() => goToOrderDetails(order.nomerok)}
                    class="flex-1"
                  >
                    Подробнее
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    on:click={() => goto('/track')}
                  >
                    Отследить
                  </Button>
                </div>
              </div>
            </Card>
          {/each}
        </div>

        <!-- Actions section -->
        <div class="mt-12 text-center">
          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <Button variant="primary" size="lg" on:click={() => goto('/create')}>
              Создать новый заказ
            </Button>
            <Button variant="outline" size="lg" on:click={() => goto('/track')}>
              Отследить заказ
            </Button>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>