<script lang="ts">
  import { onMount } from 'svelte';
  import { customersStore, type Customer } from '$lib/stores/customers';
  import { authStore } from '$lib/stores/auth';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';
  import { goto } from '$app/navigation';
  import { formatDate } from '@lolita-fashion/shared';

  // Check if user is admin
  $: user = $authStore.user;
  $: if (user && user.role !== 'admin') {
    goto('/');
  }

  let customers: Customer[] = [];
  let filteredCustomers: Customer[] = [];
  let searchTerm = '';
  let loading = false;

  $: customersData = $customersStore;
  $: customers = customersData.customers || [];
  $: loading = customersData.loading;

  // Filter customers based on search
  $: {
    if (searchTerm.trim()) {
      filteredCustomers = customers.filter(customer =>
        customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (customer.email && customer.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (customer.phone && customer.phone.includes(searchTerm))
      );
    } else {
      filteredCustomers = customers;
    }
  }

  onMount(async () => {
    // Initialize customers store if not loaded
    if (!customersData.initialized) {
      await customersStore.init();
    }
  });

  async function refreshCustomers() {
    await customersStore.loadCustomers();
  }

  async function deleteCustomer(customer: Customer) {
    if (confirm(`Вы уверены, что хотите удалить клиента "${customer.name}"?`)) {
      const result = await customersStore.deleteCustomer(customer.id);
      if (result.success) {
        // Customer will be automatically removed from the store
      } else {
        alert(`Ошибка удаления клиента: ${result.message}`);
      }
    }
  }

  function viewCustomer(customer: Customer) {
    // In future, could navigate to customer detail page
    customersStore.selectCustomer(customer);
  }
</script>

<svelte:head>
  <title>Управление клиентами - Админ панель</title>
  <meta name="description" content="Управление клиентами в админ панели" />
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm">
    <div class="container-custom py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Управление клиентами</h1>
          <p class="text-gray-600 mt-1">Просмотр и управление клиентской базой</p>
        </div>
        
        <div class="flex items-center space-x-3">
          <Button variant="outline" on:click={refreshCustomers} disabled={loading}>
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Обновить
          </Button>
          
          <a href="/admin" class="text-primary-600 hover:text-primary-700">
            ← Вернуться в админ панель
          </a>
        </div>
      </div>
    </div>
  </div>

  <div class="container-custom py-8">
    <!-- Search and filters -->
    <div class="mb-6">
      <div class="max-w-lg">
        <div class="relative">
          <Input
            placeholder="Поиск по имени, email или телефону..."
            bind:value={searchTerm}
            disabled={loading}
          />
          <svg class="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-600">Всего клиентов</p>
            <p class="text-2xl font-semibold text-gray-900">{customers.length}</p>
          </div>
          <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-600">С email</p>
            <p class="text-2xl font-semibold text-gray-900">{customers.filter(c => c.email).length}</p>
          </div>
          <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
            </svg>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-600">Результаты поиска</p>
            <p class="text-2xl font-semibold text-gray-900">{filteredCustomers.length}</p>
          </div>
          <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    {#if loading && customers.length === 0}
      <div class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p class="text-gray-500 mt-2">Загрузка клиентов...</p>
      </div>
    {:else if filteredCustomers.length === 0}
      <!-- Empty state -->
      <div class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          {searchTerm ? 'Клиенты не найдены' : 'Нет клиентов'}
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          {searchTerm ? 'Попробуйте изменить поисковый запрос' : 'Клиенты будут отображаться здесь после их создания'}
        </p>
      </div>
    {:else}
      <!-- Customers table -->
      <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <ul class="divide-y divide-gray-200">
          {#each filteredCustomers as customer (customer.id)}
            <li>
              <div class="px-4 py-4 flex items-center justify-between hover:bg-gray-50">
                <div class="flex items-center flex-1">
                  <div class="flex-shrink-0">
                    <div class="h-10 w-10 bg-gray-200 rounded-full flex items-center justify-center">
                      <span class="text-sm font-medium text-gray-700">
                        {customer.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  
                  <div class="ml-4 flex-1">
                    <div class="flex items-center">
                      <p class="text-sm font-medium text-gray-900 truncate">
                        {customer.name}
                      </p>
                    </div>
                    
                    <div class="mt-1">
                      <div class="flex items-center text-sm text-gray-500 space-x-4">
                        {#if customer.email}
                          <span class="flex items-center">
                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                            </svg>
                            {customer.email}
                          </span>
                        {/if}
                        
                        {#if customer.phone}
                          <span class="flex items-center">
                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                            </svg>
                            {customer.phone}
                          </span>
                        {/if}
                      </div>
                      
                      <div class="mt-1 text-xs text-gray-400">
                        Создан: {formatDate(customer.createdAt)}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    on:click={() => viewCustomer(customer)}
                  >
                    Просмотр
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    on:click={() => deleteCustomer(customer)}
                    class="text-red-600 hover:text-red-700 hover:border-red-300"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </Button>
                </div>
              </div>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  </div>
</div>