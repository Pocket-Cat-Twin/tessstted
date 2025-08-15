<script lang="ts">
  import { Card, Button, Badge, Spinner } from '$lib/components/ui';
  import { api } from '$lib/api/client-simple';

  // Props
  export let subscription: any = null;
  export let loading = false;

  // Subscription tiers mapping
  const tierInfo = {
    free: {
      name: 'Базовый',
      color: 'gray',
      features: ['Создание заказов', 'Базовая поддержка', 'Стандартная комиссия'],
      processingTime: '7-10 дней',
      commission: 'Стандартная',
    },
    basic: {
      name: 'Стандарт',
      color: 'blue',
      features: ['Все функции Базового', 'Приоритетная поддержка', 'Сниженная комиссия', 'Расширенная статистика'],
      processingTime: '5-7 дней',
      commission: 'Сниженная',
    },
    premium: {
      name: 'Премиум',
      color: 'purple',
      features: ['Все функции Стандарта', 'VIP поддержка', 'Минимальная комиссия', 'Приоритетная обработка', 'Персональный менеджер'],
      processingTime: '3-5 дней',
      commission: 'Минимальная',
    },
    elite: {
      name: 'Элит',
      color: 'yellow',
      features: ['Все функции Премиума', 'Без комиссии', 'Мгновенная обработка', 'Безлимитное хранение', 'VIP статус'],
      processingTime: '1-2 дня',
      commission: 'Без комиссии',
    },
  };

  // Get subscription info
  $: currentTier = subscription?.tier || 'free';
  $: tierDetails = tierInfo[currentTier] || tierInfo.free;
  $: isActive = subscription?.status === 'active';
  $: expiresAt = subscription?.expiresAt ? new Date(subscription.expiresAt) : null;
  $: daysLeft = expiresAt ? Math.max(0, Math.ceil((expiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24))) : null;

  // Format date
  function formatDate(date: Date) {
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }

  // Get status badge variant
  function getStatusVariant(status: string) {
    switch (status) {
      case 'active':
        return 'success';
      case 'expired':
        return 'danger';
      case 'cancelled':
        return 'warning';
      default:
        return 'secondary';
    }
  }
</script>

<Card variant="bordered" className="max-w-2xl mx-auto">
  <div class="space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-gray-200">
      <div>
        <h2 class="text-xl font-semibold text-gray-900">Подписка</h2>
        <p class="text-sm text-gray-600">Информация о вашем тарифном плане</p>
      </div>
    </div>

    {#if loading}
      <div class="flex justify-center py-8">
        <Spinner size="lg" />
      </div>
    {:else}
      <div class="space-y-6">
        <!-- Current Tier -->
        <div class="text-center">
          <div class={`inline-flex items-center justify-center w-20 h-20 rounded-full mb-4 ${
            tierDetails.color === 'gray' ? 'bg-gray-100' :
            tierDetails.color === 'blue' ? 'bg-blue-100' :
            tierDetails.color === 'purple' ? 'bg-purple-100' :
            'bg-yellow-100'
          }`}>
            <span class={`text-3xl ${
              tierDetails.color === 'gray' ? 'text-gray-600' :
              tierDetails.color === 'blue' ? 'text-blue-600' :
              tierDetails.color === 'purple' ? 'text-purple-600' :
              'text-yellow-600'
            }`}>
              {currentTier === 'free' ? '🆓' : 
               currentTier === 'basic' ? '⭐' :
               currentTier === 'premium' ? '💎' : '👑'}
            </span>
          </div>
          
          <h3 class="text-2xl font-bold text-gray-900 mb-2">
            {tierDetails.name}
          </h3>
          
          <div class="flex items-center justify-center space-x-2">
            <Badge variant={getStatusVariant(subscription?.status || 'inactive')}>
              {subscription?.status === 'active' ? 'Активна' :
               subscription?.status === 'expired' ? 'Истекла' :
               subscription?.status === 'cancelled' ? 'Отменена' :
               'Неактивна'}
            </Badge>
            
            {#if isActive && daysLeft !== null}
              <span class="text-sm text-gray-600">
                • {daysLeft} дн. осталось
              </span>
            {/if}
          </div>
        </div>

        <!-- Subscription Details -->
        {#if subscription && isActive}
          <div class="bg-gray-50 rounded-lg p-4 space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">Активна с</dt>
                <dd class="text-sm text-gray-900">
                  {formatDate(new Date(subscription.activatedAt))}
                </dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">Действует до</dt>
                <dd class="text-sm text-gray-900">
                  {expiresAt ? formatDate(expiresAt) : 'Не указано'}
                </dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">Время обработки</dt>
                <dd class="text-sm text-gray-900">{tierDetails.processingTime}</dd>
              </div>
              
              <div>
                <dt class="text-sm font-medium text-gray-500">Комиссия</dt>
                <dd class="text-sm text-gray-900">{tierDetails.commission}</dd>
              </div>
            </div>
          </div>
        {/if}

        <!-- Features -->
        <div>
          <h4 class="text-lg font-medium text-gray-900 mb-3">Возможности тарифа</h4>
          <ul class="space-y-2">
            {#each tierDetails.features as feature}
              <li class="flex items-start space-x-2">
                <span class="text-green-500 mt-0.5">✓</span>
                <span class="text-sm text-gray-600">{feature}</span>
              </li>
            {/each}
          </ul>
        </div>

        <!-- Actions -->
        <div class="flex justify-center space-x-3 pt-4 border-t border-gray-200">
          {#if currentTier === 'free'}
            <Button className="bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700">
              Улучшить тариф
            </Button>
          {:else if !isActive}
            <Button variant="outline">
              Продлить подписку
            </Button>
          {:else}
            <Button variant="outline">
              Изменить тариф
            </Button>
          {/if}
          
          <Button variant="outline">
            История подписок
          </Button>
        </div>

        <!-- Upgrade Suggestion -->
        {#if currentTier !== 'elite'}
          <div class="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-lg p-4">
            <div class="flex items-start space-x-3">
              <span class="text-pink-500 text-xl">💝</span>
              <div>
                <h5 class="font-medium text-gray-900 mb-1">Хотите больше возможностей?</h5>
                <p class="text-sm text-gray-600 mb-3">
                  Улучшите ваш тариф и получите доступ к дополнительным функциям, 
                  более быстрой обработке заказов и сниженным комиссиям.
                </p>
                <Button size="sm" variant="outline">
                  Сравнить тарифы
                </Button>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</Card>