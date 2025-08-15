<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth';
  import { api } from '$lib/api/client-simple';
  import { Card, Button, Badge, Spinner, Toast } from '$lib/components/ui';

  // State
  let subscriptionTiers: any[] = [];
  let currentSubscription: any = null;
  let loading = true;
  let toastMessage = '';
  let toastType: 'success' | 'error' = 'success';
  let showToast = false;

  // Auth state
  let authState: any;
  authStore.subscribe(state => {
    authState = state;
  });

  // Load subscription data
  async function loadSubscriptionData() {
    try {
      // Load subscription tiers (public)
      const tiersResponse = await api.getSubscriptionTiers();
      if (tiersResponse.success) {
        subscriptionTiers = tiersResponse.data.tiers;
      }

      // Load current subscription if authenticated
      if (authState?.user) {
        const statusResponse = await api.getSubscriptionStatus();
        if (statusResponse.success) {
          currentSubscription = statusResponse.data.subscription;
        }
      }
    } catch (error) {
      showMessage('Ошибка загрузки данных', 'error');
    } finally {
      loading = false;
    }
  }

  // Show toast message
  function showMessage(message: string, type: 'success' | 'error' = 'success') {
    toastMessage = message;
    toastType = type;
    showToast = true;
    
    setTimeout(() => {
      showToast = false;
    }, 5000);
  }

  // Get tier details and styling
  function getTierInfo(tierId: string) {
    const tierStyles = {
      free: {
        gradient: 'from-gray-100 to-gray-200',
        buttonClass: 'bg-gray-600 hover:bg-gray-700',
        iconColor: 'text-gray-600',
        icon: '🔧',
        isPopular: false,
        badge: null,
      },
      group: {
        gradient: 'from-blue-100 to-blue-200',
        buttonClass: 'bg-blue-600 hover:bg-blue-700',
        iconColor: 'text-blue-600',
        icon: '👥',
        isPopular: true,
        badge: 'Популярный',
      },
      elite: {
        gradient: 'from-purple-100 to-purple-200',
        buttonClass: 'bg-purple-600 hover:bg-purple-700',
        iconColor: 'text-purple-600',
        icon: '💎',
        isPopular: false,
        badge: 'Премиум',
      },
      vip_temp: {
        gradient: 'from-yellow-100 to-yellow-200',
        buttonClass: 'bg-yellow-600 hover:bg-yellow-700',
        iconColor: 'text-yellow-600',
        icon: '⚡',
        isPopular: false,
        badge: 'Срочно',
      },
    };

    return tierStyles[tierId] || tierStyles.free;
  }

  // Format price
  function formatPrice(price: number, currency: string = 'RUB') {
    if (price === 0) return 'Бесплатно';
    return `${price.toLocaleString()} ₽`;
  }

  // Format duration
  function formatDuration(days: number | null) {
    if (!days) return 'Постоянно';
    if (days === 7) return '7 дней';
    if (days === 30) return '1 месяц';
    return `${days} дней`;
  }

  // Handle subscription upgrade
  function handleUpgrade(tier: any) {
    if (!authState?.user) {
      goto('/login');
      return;
    }

    // For now, just show a message
    showMessage(`Функция подписки "${tier.name}" в разработке`, 'success');
  }

  // Check if tier is current
  function isCurrentTier(tierId: string) {
    return currentSubscription?.tier === tierId && currentSubscription?.status === 'active';
  }

  // Initialize
  onMount(() => {
    loadSubscriptionData();
  });
</script>

<svelte:head>
  <title>Тарифы и подписки - YuYu Lolita Shopping</title>
  <meta name="description" content="Выберите подходящий тарифный план для работы с YuYu Lolita Shopping. Различные уровни обслуживания для любых потребностей.">
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 via-white to-purple-50 py-12">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    
    <!-- Header -->
    <div class="text-center mb-16">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Тарифы и подписки
      </h1>
      <p class="text-xl text-gray-600 max-w-3xl mx-auto">
        Выберите тарифный план, который лучше всего подходит для ваших потребностей в shopping-услугах
      </p>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <Spinner size="xl" />
      </div>
    {:else}
      <!-- Current Subscription Status -->
      {#if authState?.user && currentSubscription}
        <div class="mb-12">
          <Card variant="shadow" className="max-w-2xl mx-auto bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
            <div class="flex items-center space-x-4">
              <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <span class="text-2xl">✅</span>
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">
                  Ваша текущая подписка
                </h3>
                <p class="text-gray-600">
                  {subscriptionTiers.find(t => t.id === currentSubscription.tier)?.name || 'Неизвестный тариф'}
                  {#if currentSubscription.expiresAt}
                    - действует до {new Date(currentSubscription.expiresAt).toLocaleDateString('ru-RU')}
                  {/if}
                </p>
              </div>
            </div>
          </Card>
        </div>
      {/if}

      <!-- Subscription Tiers -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        {#each subscriptionTiers as tier}
          {@const tierInfo = getTierInfo(tier.id)}
          <div class="relative">
            <!-- Popular badge -->
            {#if tierInfo.isPopular}
              <div class="absolute -top-3 left-1/2 transform -translate-x-1/2 z-10">
                <Badge variant="primary" className="px-3 py-1">
                  {tierInfo.badge}
                </Badge>
              </div>
            {/if}

            <Card 
              variant={tierInfo.isPopular ? 'shadow' : 'bordered'}
              className={`h-full transition-all duration-300 hover:scale-105 ${
                tierInfo.isPopular ? 'border-2 border-pink-300 shadow-lg' : ''
              } ${isCurrentTier(tier.id) ? 'ring-2 ring-green-500 ring-opacity-50' : ''}`}
            >
              <div class="space-y-6">
                <!-- Header -->
                <div class="text-center">
                  <div class={`w-16 h-16 bg-gradient-to-br ${tierInfo.gradient} rounded-full flex items-center justify-center mx-auto mb-4`}>
                    <span class={`text-3xl ${tierInfo.iconColor}`}>
                      {tierInfo.icon}
                    </span>
                  </div>
                  
                  <h3 class="text-xl font-bold text-gray-900 mb-2">
                    {tier.name}
                  </h3>
                  
                  <p class="text-sm text-gray-600 mb-4">
                    {tier.description}
                  </p>
                  
                  <!-- Price -->
                  <div class="text-center">
                    <span class="text-3xl font-bold text-gray-900">
                      {formatPrice(tier.price, tier.currency)}
                    </span>
                    {#if tier.price > 0}
                      <span class="text-gray-600 text-sm ml-1">
                        / {formatDuration(tier.duration)}
                      </span>
                    {/if}
                  </div>
                </div>

                <!-- Features -->
                <div class="space-y-3">
                  <h4 class="font-medium text-gray-900 text-sm">Возможности:</h4>
                  <ul class="space-y-2">
                    {#each tier.features as feature}
                      <li class="flex items-start space-x-2 text-sm">
                        <span class="text-green-500 mt-0.5">✓</span>
                        <span class="text-gray-600">{feature}</span>
                      </li>
                    {/each}
                  </ul>
                </div>

                <!-- Limitations -->
                {#if tier.limitations && tier.limitations.length > 0}
                  <div class="space-y-3">
                    <h4 class="font-medium text-gray-900 text-sm">Ограничения:</h4>
                    <ul class="space-y-2">
                      {#each tier.limitations as limitation}
                        <li class="flex items-start space-x-2 text-sm">
                          <span class="text-orange-500 mt-0.5">⚠</span>
                          <span class="text-gray-600">{limitation}</span>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}

                <!-- Action Button -->
                <div class="pt-4">
                  {#if isCurrentTier(tier.id)}
                    <Button 
                      variant="outline" 
                      className="w-full"
                      disabled
                    >
                      Текущий тариф
                    </Button>
                  {:else if tier.id === 'free'}
                    <Button 
                      variant="outline" 
                      className="w-full"
                    >
                      Базовый тариф
                    </Button>
                  {:else}
                    <Button 
                      className={`w-full text-white ${tierInfo.buttonClass}`}
                      on:click={() => handleUpgrade(tier)}
                    >
                      {authState?.user ? 'Выбрать тариф' : 'Войти и выбрать'}
                    </Button>
                  {/if}
                </div>
              </div>
            </Card>
          </div>
        {/each}
      </div>

      <!-- Additional Information -->
      <div class="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- FAQ -->
        <Card variant="bordered">
          <div class="space-y-6">
            <h3 class="text-xl font-semibold text-gray-900">Часто задаваемые вопросы</h3>
            
            <div class="space-y-4">
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Как работает подписка?</h4>
                <p class="text-sm text-gray-600">
                  Подписка активируется сразу после оплаты и предоставляет доступ к расширенным функциям в течение указанного периода.
                </p>
              </div>
              
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Можно ли изменить тариф?</h4>
                <p class="text-sm text-gray-600">
                  Да, вы можете повысить тариф в любое время. При понижении тарифа изменения вступят в силу после окончания текущего периода.
                </p>
              </div>
              
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Что происходит после окончания подписки?</h4>
                <p class="text-sm text-gray-600">
                  После окончания подписки ваш аккаунт переходит на базовый тариф с соответствующими ограничениями.
                </p>
              </div>
            </div>
          </div>
        </Card>

        <!-- Support -->
        <Card variant="bordered">
          <div class="space-y-6">
            <h3 class="text-xl font-semibold text-gray-900">Нужна помощь?</h3>
            
            <div class="space-y-4">
              <div class="flex items-start space-x-3">
                <span class="text-pink-500 text-lg">💬</span>
                <div>
                  <h4 class="font-medium text-gray-900">Свяжитесь с поддержкой</h4>
                  <p class="text-sm text-gray-600 mb-2">
                    Наша команда поможет выбрать подходящий тариф
                  </p>
                  <Button variant="outline" size="sm">
                    Написать в поддержку
                  </Button>
                </div>
              </div>
              
              <div class="flex items-start space-x-3">
                <span class="text-blue-500 text-lg">📖</span>
                <div>
                  <h4 class="font-medium text-gray-900">Подробная документация</h4>
                  <p class="text-sm text-gray-600 mb-2">
                    Узнайте больше о возможностях каждого тарифа
                  </p>
                  <Button variant="outline" size="sm" href="/faq">
                    Перейти в FAQ
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Call to Action -->
      {#if !authState?.user}
        <div class="mt-16 text-center">
          <Card variant="shadow" className="max-w-2xl mx-auto bg-gradient-to-r from-pink-50 to-purple-50">
            <div class="space-y-4">
              <h3 class="text-2xl font-bold text-gray-900">
                Готовы начать?
              </h3>
              <p class="text-gray-600">
                Зарегистрируйтесь сейчас и получите доступ к нашим services
              </p>
              <div class="flex justify-center space-x-4">
                <Button href="/register" className="bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700">
                  Зарегистрироваться
                </Button>
                <Button variant="outline" href="/login">
                  Войти
                </Button>
              </div>
            </div>
          </Card>
        </div>
      {/if}
    {/if}
  </div>
</div>

<!-- Toast Notification -->
{#if showToast}
  <Toast 
    message={toastMessage} 
    type={toastType} 
    onClose={() => showToast = false}
  />
{/if}