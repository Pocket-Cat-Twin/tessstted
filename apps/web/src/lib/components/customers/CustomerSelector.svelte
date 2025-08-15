<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { customersStore, type Customer } from '$lib/stores/customers';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';

  export let selectedCustomer: Customer | null = null;
  export let disabled = false;

  const dispatch = createEventDispatcher<{
    select: Customer;
    clear: void;
  }>();

  let searchTerm = '';
  let showDropdown = false;
  let filteredCustomers: Customer[] = [];
  let searchInput: HTMLInputElement;

  $: customers = $customersStore.customers;
  $: loading = $customersStore.loading;

  // Filter customers based on search term
  $: {
    if (searchTerm.trim()) {
      filteredCustomers = customers.filter(customer =>
        customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (customer.email && customer.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (customer.phone && customer.phone.includes(searchTerm))
      );
    } else {
      filteredCustomers = customers.slice(0, 10); // Show first 10 customers
    }
  }

  onMount(async () => {
    if (!$customersStore.initialized) {
      await customersStore.init();
    }
  });

  function handleSearch() {
    showDropdown = true;
  }

  function selectCustomer(customer: Customer) {
    selectedCustomer = customer;
    searchTerm = customer.name;
    showDropdown = false;
    customersStore.selectCustomer(customer);
    dispatch('select', customer);
  }

  function clearSelection() {
    selectedCustomer = null;
    searchTerm = '';
    showDropdown = false;
    customersStore.selectCustomer(null);
    dispatch('clear');
  }

  function handleInputFocus() {
    if (!disabled) {
      showDropdown = true;
    }
  }

  function handleInputBlur() {
    // Delay hiding dropdown to allow clicks on options
    setTimeout(() => {
      showDropdown = false;
    }, 200);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      showDropdown = false;
    }
  }
</script>

<div class="relative" on:keydown={handleKeydown}>
  <div class="flex gap-2">
    <div class="flex-1 relative">
      <Input
        bind:element={searchInput}
        bind:value={searchTerm}
        placeholder="Поиск клиента по имени, email или телефону..."
        {disabled}
        on:input={handleSearch}
        on:focus={handleInputFocus}
        on:blur={handleInputBlur}
      />
      
      <!-- Dropdown with search results -->
      {#if showDropdown && !disabled}
        <div class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {#if loading}
            <div class="p-3 text-center text-gray-500">
              Загрузка клиентов...
            </div>
          {:else if filteredCustomers.length > 0}
            <div class="py-1">
              {#each filteredCustomers as customer (customer.id)}
                <button
                  type="button"
                  class="w-full px-3 py-2 text-left hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
                  on:click={() => selectCustomer(customer)}
                >
                  <div class="flex justify-between items-start">
                    <div>
                      <div class="font-medium text-gray-900">
                        {customer.name}
                      </div>
                      {#if customer.email || customer.phone}
                        <div class="text-sm text-gray-500">
                          {#if customer.email}{customer.email}{/if}
                          {#if customer.email && customer.phone} • {/if}
                          {#if customer.phone}{customer.phone}{/if}
                        </div>
                      {/if}
                    </div>
                  </div>
                </button>
              {/each}
            </div>
          {:else}
            <div class="p-3 text-center text-gray-500">
              {searchTerm.trim() ? 'Клиенты не найдены' : 'Нет доступных клиентов'}
            </div>
          {/if}
        </div>
      {/if}
    </div>
    
    {#if selectedCustomer}
      <Button
        variant="outline" 
        size="sm"
        on:click={clearSelection}
        {disabled}
      >
        Очистить
      </Button>
    {/if}
  </div>

  <!-- Selected customer info -->
  {#if selectedCustomer}
    <div class="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
      <div class="flex justify-between items-start">
        <div>
          <div class="font-medium text-blue-900">
            {selectedCustomer.name}
          </div>
          <div class="text-sm text-blue-700">
            {#if selectedCustomer.email}{selectedCustomer.email}{/if}
            {#if selectedCustomer.email && selectedCustomer.phone} • {/if}
            {#if selectedCustomer.phone}{selectedCustomer.phone}{/if}
          </div>
          {#if selectedCustomer.addresses && selectedCustomer.addresses.length > 0}
            <div class="mt-1 text-sm text-blue-600">
              Адресов: {selectedCustomer.addresses.length}
            </div>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  /* Custom scrollbar for dropdown */
  .overflow-y-auto::-webkit-scrollbar {
    width: 6px;
  }
  .overflow-y-auto::-webkit-scrollbar-track {
    background: #f1f1f1;
  }
  .overflow-y-auto::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }
  .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
  }
</style>