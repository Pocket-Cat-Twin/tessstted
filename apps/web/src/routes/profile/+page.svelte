<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth';
  import { api } from '$lib/api/client-simple';
  import { Card, Button, Spinner, Toast } from '$lib/components/ui';
  import ProfileEditForm from '$lib/components/profile/ProfileEditForm.svelte';
  import AddressManager from '$lib/components/profile/AddressManager.svelte';
  import SubscriptionCard from '$lib/components/profile/SubscriptionCard.svelte';

  // State
  let profile: any = null;
  let addresses: any[] = [];
  let subscription: any = null;
  let loading = true;
  let activeTab = 'profile'; // profile, addresses, subscription
  let toastMessage = '';
  let toastType: 'success' | 'error' = 'success';
  let showToast = false;

  // Auth state
  let authState: any;
  authStore.subscribe(state => {
    authState = state;
    
    // Redirect if not authenticated
    if (state.initialized && !state.user) {
      goto('/login');
    }
  });

  // Load profile data
  async function loadProfile() {
    try {
      const response = await api.getProfile();
      if (response.success) {
        profile = response.data.profile;
        addresses = profile.addresses || [];
        subscription = profile.subscription;
      } else {
        showMessage('Ошибка загрузки профиля', 'error');
      }
    } catch (error) {
      showMessage('Ошибка подключения к серверу', 'error');
    } finally {
      loading = false;
    }
  }

  // Load addresses
  async function loadAddresses() {
    try {
      const response = await api.getAddresses();
      if (response.success) {
        addresses = response.data.addresses || [];
      }
    } catch (error) {
      console.error('Failed to load addresses:', error);
    }
  }

  // Load subscription
  async function loadSubscription() {
    try {
      const response = await api.getSubscription();
      if (response.success) {
        subscription = response.data.subscription;
      }
    } catch (error) {
      console.error('Failed to load subscription:', error);
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

  // Handle profile update success
  function handleProfileSuccess(event: CustomEvent) {
    showMessage(event.detail.message, 'success');
    loadProfile(); // Reload profile data
  }

  // Handle profile update error
  function handleProfileError(event: CustomEvent) {
    showMessage(event.detail.message, 'error');
  }

  // Handle address operations
  function handleAddressSuccess(event: CustomEvent) {
    showMessage(event.detail.message, 'success');
  }

  function handleAddressError(event: CustomEvent) {
    showMessage(event.detail.message, 'error');
  }

  function handleAddressRefresh() {
    loadAddresses();
  }

  // Tab navigation
  const tabs = [
    { id: 'profile', label: 'Профиль', icon: '👤' },
    { id: 'addresses', label: 'Адреса', icon: '📍' },
    { id: 'subscription', label: 'Подписка', icon: '⭐' },
  ];

  // Initialize
  onMount(() => {
    if (authState?.user) {
      loadProfile();
    }
  });
</script>

<svelte:head>
  <title>Профиль - YuYu Lolita Shopping</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 via-white to-purple-50 py-8">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
    
    <!-- Header -->
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">Мой профиль</h1>
      <p class="text-gray-600">Управление личными данными и настройками</p>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <Spinner size="xl" />
      </div>
    {:else}
      <!-- Tab Navigation -->
      <div class="mb-8">
        <nav class="flex space-x-8 justify-center" aria-label="Tabs">
          {#each tabs as tab}
            <button
              on:click={() => activeTab = tab.id}
              class={`${
                activeTab === tab.id
                  ? 'border-pink-500 text-pink-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors`}
            >
              <span class="text-lg">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          {/each}
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="space-y-8">
        {#if activeTab === 'profile'}
          <ProfileEditForm 
            {profile} 
            {loading}
            on:success={handleProfileSuccess}
            on:error={handleProfileError}
            on:cancel={() => {}}
          />
        {:else if activeTab === 'addresses'}
          <AddressManager 
            {addresses} 
            loading={false}
            on:success={handleAddressSuccess}
            on:error={handleAddressError}
            on:refresh={handleAddressRefresh}
          />
        {:else if activeTab === 'subscription'}
          <SubscriptionCard 
            {subscription} 
            loading={false}
          />
        {/if}
      </div>

      <!-- Quick Actions -->
      <div class="mt-12 max-w-2xl mx-auto">
        <Card variant="shadow" class="text-center">
          <div class="space-y-4">
            <h3 class="text-lg font-semibold text-gray-900">Быстрые действия</h3>
            <div class="flex flex-wrap justify-center gap-3">
              <Button variant="outline" size="sm" on:click={() => goto('/orders')}>
                📦 Мои заказы
              </Button>
              <Button variant="outline" size="sm" on:click={() => goto('/create')}>
                ➕ Создать заказ
              </Button>
              <Button variant="outline" size="sm" on:click={() => goto('/track')}>
                🔍 Отследить заказ
              </Button>
              <Button variant="outline" size="sm" on:click={() => authStore.logout()}>
                🚪 Выйти
              </Button>
            </div>
          </div>
        </Card>
      </div>
    {/if}
  </div>
</div>

<!-- Toast Notification -->
{#if showToast}
  <Toast 
    message={toastMessage} 
    type={toastType} 
    on:dismiss={() => showToast = false}
  />
{/if}

<style>
  /* Custom styles for better visual hierarchy */
  :global(.profile-section) {
    transform: scale(1);
    transition: all 0.2s ease;
  }
  
  :global(.profile-section:hover) {
    transform: scale(1.02);
  }
</style>