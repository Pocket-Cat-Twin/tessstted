<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { ordersStore } from '$lib/stores/orders';
  import { configStore } from '$lib/stores/config';
  import Button from '$components/ui/Button.svelte';
  import Input from '$components/ui/Input.svelte';
  import Modal from '$components/ui/Modal.svelte';
  import { formatCurrency, calculateOrderTotals } from '@yuyu/shared';

  // Form data
  let customerName = '';
  let customerPhone = '';
  let customerEmail = '';
  let deliveryAddress = '';
  let deliveryMethod = 'Почта России';
  let paymentMethod = 'Банковская карта';
  
  // Goods array
  let goods: Array<{
    name: string;
    link: string;
    quantity: number;
    priceYuan: number;
  }> = [{ name: '', link: '', quantity: 1, priceYuan: 0 }];

  // State
  let loading = false;
  let error = '';
  let showSuccessModal = false;
  let createdOrder: any = null;

  // Config
  $: config = $configStore.config;
  $: currentKurs = $configStore.kurs;
  
  // Calculations
  $: totals = calculateOrderTotals(goods, currentKurs, 0.1); // 10% commission
  $: isFormValid = customerName && customerPhone && deliveryAddress && goods.every(g => g.name && g.quantity > 0 && g.priceYuan > 0);

  onMount(() => {
    // Initialize config if not loaded
    if (!$configStore.initialized) {
      configStore.init();
    }
  });

  function addGood() {
    goods = [...goods, { name: '', link: '', quantity: 1, priceYuan: 0 }];
  }

  function removeGood(index: number) {
    if (goods.length > 1) {
      goods = goods.filter((_, i) => i !== index);
    }
  }

  function handleGoodChange(index: number, field: string, value: any) {
    goods[index] = { ...goods[index], [field]: value };
    goods = [...goods]; // Trigger reactivity
  }

  async function handleSubmit() {
    if (!isFormValid) {
      error = 'Пожалуйста, заполните все обязательные поля';
      return;
    }

    loading = true;
    error = '';

    const orderData = {
      customerName,
      customerPhone,
      customerEmail: customerEmail || undefined,
      deliveryAddress,
      deliveryMethod,
      paymentMethod,
      goods: goods.filter(g => g.name && g.quantity > 0 && g.priceYuan > 0)
    };

    const result = await ordersStore.create(orderData);
    loading = false;

    if (result.success) {
      createdOrder = result.order;
      showSuccessModal = true;
      // Clear form
      resetForm();
    } else {
      error = result.message || 'Ошибка создания заказа';
    }
  }

  function resetForm() {
    customerName = '';
    customerPhone = '';
    customerEmail = '';
    deliveryAddress = '';
    deliveryMethod = 'Почта России';
    paymentMethod = 'Банковская карта';
    goods = [{ name: '', link: '', quantity: 1, priceYuan: 0 }];
  }

  function handleSuccessConfirm() {
    showSuccessModal = false;
    if (createdOrder?.nomerok) {
      goto(`/order/${createdOrder.nomerok}`);
    }
  }
</script>

<svelte:head>
  <title>Создать заказ - YuYu Lolita Shopping</title>
  <meta name="description" content="Создайте заказ товаров из Китая с помощью YuYu Lolita Shopping" />
</svelte:head>

<!-- Success Modal -->
<Modal 
  bind:open={showSuccessModal} 
  title="Заказ создан успешно!"
  size="md"
  on:confirm={handleSuccessConfirm}
>
  <div class="text-center space-y-4">
    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
      <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
    </div>
    
    {#if createdOrder}
      <div>
        <p class="text-gray-600">Ваш заказ был успешно создан!</p>
        <p class="text-lg font-semibold text-gray-900 mt-2">
          Номер заказа: <span class="text-primary-600">{createdOrder.nomerok}</span>
        </p>
        <p class="text-sm text-gray-500 mt-2">
          Сохраните этот номер для отслеживания заказа
        </p>
      </div>
    {/if}
  </div>

  <svelte:fragment slot="footer" let:close let:confirm>
    <div class="flex items-center justify-center gap-3 p-6 border-t border-gray-200 bg-gray-50">
      <Button variant="outline" on:click={close}>
        Создать еще заказ
      </Button>
      <Button variant="primary" on:click={confirm}>
        Перейти к заказу
      </Button>
    </div>
  </svelte:fragment>
</Modal>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm">
    <div class="container-custom py-8">
      <div class="text-center">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          Создать заказ
        </h1>
        <p class="text-lg text-gray-600 max-w-2xl mx-auto">
          Заполните форму ниже, и мы поможем вам заказать товары из Китая
        </p>
      </div>
    </div>
  </div>

  <div class="container-custom py-8">
    <form on:submit|preventDefault={handleSubmit} class="max-w-4xl mx-auto">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Main Form -->
        <div class="lg:col-span-2 space-y-8">
          <!-- Customer Information -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              Контактная информация
            </h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Имя и фамилия"
                placeholder="Иван Иванов"
                bind:value={customerName}
                required
                disabled={loading}
              />
              
              <Input
                label="Телефон"
                type="tel"
                placeholder="+7 (999) 123-45-67"
                bind:value={customerPhone}
                required
                disabled={loading}
              />
              
              <div class="md:col-span-2">
                <Input
                  label="Email (необязательно)"
                  type="email"
                  placeholder="ivan@example.com"
                  bind:value={customerEmail}
                  disabled={loading}
                  helperText="Для отправки уведомлений о статусе заказа"
                />
              </div>
            </div>
          </div>

          <!-- Delivery Information -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Доставка
            </h2>
            
            <div class="space-y-4">
              <div>
                <Input
                  label="Адрес доставки"
                  placeholder="Город, улица, дом, квартира"
                  bind:value={deliveryAddress}
                  required
                  disabled={loading}
                />
              </div>
              
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label for="deliveryMethod" class="form-label">Способ доставки</label>
                  <select 
                    id="deliveryMethod"
                    bind:value={deliveryMethod}
                    class="form-input"
                    disabled={loading}
                  >
                    <option value="Почта России">Почта России</option>
                    <option value="СДЭК">СДЭК</option>
                    <option value="Boxberry">Boxberry</option>
                    <option value="Самовывоз">Самовывоз</option>
                  </select>
                </div>
                
                <div>
                  <label for="paymentMethod" class="form-label">Способ оплаты</label>
                  <select 
                    id="paymentMethod"
                    bind:value={paymentMethod}
                    class="form-input"
                    disabled={loading}
                  >
                    <option value="Банковская карта">Банковская карта</option>
                    <option value="СБП">СБП (Система быстрых платежей)</option>
                    <option value="Наличные при получении">Наличные при получении</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- Goods -->
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-semibold text-gray-900 flex items-center">
                <svg class="w-5 h-5 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                Товары
              </h2>
              
              <Button
                type="button"
                variant="outline"
                size="sm"
                on:click={addGood}
                disabled={loading}
              >
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Добавить товар
              </Button>
            </div>
            
            <div class="space-y-4">
              {#each goods as good, index}
                <div class="border border-gray-200 rounded-lg p-4">
                  <div class="flex items-center justify-between mb-4">
                    <h3 class="font-medium text-gray-900">Товар {index + 1}</h3>
                    {#if goods.length > 1}
                      <button
                        type="button"
                        on:click={() => removeGood(index)}
                        class="text-red-500 hover:text-red-700 p-1"
                        disabled={loading}
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    {/if}
                  </div>
                  
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="md:col-span-2">
                      <Input
                        label="Название товара"
                        placeholder="Название или описание товара"
                        value={good.name}
                        on:input={(e) => handleGoodChange(index, 'name', e.target.value)}
                        required
                        disabled={loading}
                      />
                    </div>
                    
                    <div class="md:col-span-2">
                      <Input
                        label="Ссылка на товар (необязательно)"
                        type="url"
                        placeholder="https://example.com/product"
                        value={good.link}
                        on:input={(e) => handleGoodChange(index, 'link', e.target.value)}
                        disabled={loading}
                      />
                    </div>
                    
                    <Input
                      label="Количество"
                      type="number"
                      min="1"
                      value={good.quantity}
                      on:input={(e) => handleGoodChange(index, 'quantity', parseInt(e.target.value) || 1)}
                      required
                      disabled={loading}
                    />
                    
                    <Input
                      label="Цена за единицу (¥)"
                      type="number"
                      min="0"
                      step="0.01"
                      value={good.priceYuan}
                      on:input={(e) => handleGoodChange(index, 'priceYuan', parseFloat(e.target.value) || 0)}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>
              {/each}
            </div>
          </div>

          <!-- Error Message -->
          {#if error}
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          {/if}

          <!-- Submit Button -->
          <div class="flex justify-center">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              {loading}
              disabled={loading || !isFormValid}
              class="px-8"
            >
              {loading ? 'Создание заказа...' : 'Создать заказ'}
            </Button>
          </div>
        </div>

        <!-- Order Summary -->
        <div class="lg:col-span-1">
          <div class="sticky top-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 class="text-lg font-semibold text-gray-900 mb-4">
                Расчет стоимости
              </h3>
              
              <div class="space-y-3 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Товары (¥):</span>
                  <span class="font-medium">¥{totals.subtotalYuan.toFixed(2)}</span>
                </div>
                
                <div class="flex justify-between">
                  <span class="text-gray-600">Комиссия 10% (¥):</span>
                  <span class="font-medium">¥{totals.totalCommission.toFixed(2)}</span>
                </div>
                
                <div class="flex justify-between">
                  <span class="text-gray-600">Итого (¥):</span>
                  <span class="font-medium">¥{totals.totalYuan.toFixed(2)}</span>
                </div>
                
                <hr class="my-3" />
                
                <div class="flex justify-between">
                  <span class="text-gray-600">Курс:</span>
                  <span class="font-medium">{currentKurs} ₽/¥</span>
                </div>
                
                <div class="flex justify-between text-lg font-semibold text-primary-600">
                  <span>К оплате:</span>
                  <span>{formatCurrency(totals.totalRuble, 'RUB')}</span>
                </div>
              </div>
              
              <div class="mt-6 p-4 bg-blue-50 rounded-lg">
                <div class="flex items-start space-x-2">
                  <svg class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div class="text-sm text-blue-700">
                    <p class="font-medium mb-1">Обратите внимание:</p>
                    <ul class="space-y-1 text-xs">
                      <li>• Стоимость доставки рассчитывается отдельно</li>
                      <li>• Итоговая цена может измениться при колебании курса</li>
                      <li>• После создания заказа с вами свяжется менеджер</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </form>
  </div>
</div>

<style>
  .form-input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors;
  }
  
  .form-label {
    @apply block text-sm font-medium text-gray-700 mb-1;
  }
</style>