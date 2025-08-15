<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Card, Button, Input, Modal, Spinner } from '$lib/components/ui';
  import { api } from '$lib/api/client-simple';

  // Props
  export let addresses: any[] = [];
  export let loading = false;

  // State
  let showAddModal = false;
  let editingAddress: any = null;
  let savingAddress = false;
  let deletingAddressId = '';

  // Form data for new/edit address
  let addressForm = {
    fullAddress: '',
    city: '',
    postalCode: '',
    country: 'Россия',
    addressComments: '',
    isDefault: false,
  };

  // Validation errors
  let errors: Record<string, string> = {};

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Reset form
  function resetForm() {
    addressForm = {
      fullAddress: '',
      city: '',
      postalCode: '',
      country: 'Россия',
      addressComments: '',
      isDefault: false,
    };
    errors = {};
  }

  // Open add modal
  function openAddModal() {
    resetForm();
    editingAddress = null;
    showAddModal = true;
  }

  // Open edit modal
  function openEditModal(address: any) {
    addressForm = {
      fullAddress: address.fullAddress || '',
      city: address.city || '',
      postalCode: address.postalCode || '',
      country: address.country || 'Россия',
      addressComments: address.addressComments || '',
      isDefault: address.isDefault || false,
    };
    editingAddress = address;
    errors = {};
    showAddModal = true;
  }

  // Validate form
  function validateForm() {
    errors = {};
    
    if (!addressForm.fullAddress.trim()) {
      errors.fullAddress = 'Полный адрес обязателен';
    }
    
    if (!addressForm.city.trim()) {
      errors.city = 'Город обязателен';
    }

    return Object.keys(errors).length === 0;
  }

  // Save address
  async function saveAddress() {
    if (!validateForm()) return;

    savingAddress = true;
    
    try {
      let response;
      
      if (editingAddress) {
        // Update existing address
        response = await api.updateAddress(editingAddress.id, addressForm);
      } else {
        // Add new address
        response = await api.addAddress(addressForm);
      }
      
      if (response.success) {
        showAddModal = false;
        dispatch('success', { 
          message: editingAddress ? 'Адрес обновлен' : 'Адрес добавлен' 
        });
        dispatch('refresh');
      } else {
        dispatch('error', { 
          message: response.message || 'Ошибка при сохранении адреса' 
        });
      }
    } catch (error) {
      dispatch('error', { message: 'Ошибка подключения к серверу' });
    } finally {
      savingAddress = false;
    }
  }

  // Delete address
  async function deleteAddress(addressId: string) {
    if (!confirm('Вы уверены, что хотите удалить этот адрес?')) return;

    deletingAddressId = addressId;
    
    try {
      const response = await api.deleteAddress(addressId);
      
      if (response.success) {
        dispatch('success', { message: 'Адрес удален' });
        dispatch('refresh');
      } else {
        dispatch('error', { 
          message: response.message || 'Ошибка при удалении адреса' 
        });
      }
    } catch (error) {
      dispatch('error', { message: 'Ошибка подключения к серверу' });
    } finally {
      deletingAddressId = '';
    }
  }

  // Set default address
  async function setDefaultAddress(address: any) {
    try {
      const response = await api.updateAddress(address.id, { isDefault: true });
      
      if (response.success) {
        dispatch('success', { message: 'Адрес по умолчанию изменен' });
        dispatch('refresh');
      } else {
        dispatch('error', { 
          message: response.message || 'Ошибка при обновлении адреса' 
        });
      }
    } catch (error) {
      dispatch('error', { message: 'Ошибка подключения к серверу' });
    }
  }
</script>

<Card variant="bordered" className="max-w-4xl mx-auto">
  <div class="space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-gray-200">
      <div>
        <h2 class="text-xl font-semibold text-gray-900">Адреса доставки</h2>
        <p class="text-sm text-gray-600">Управление адресами для доставки заказов</p>
      </div>
      <Button on:click={openAddModal} disabled={loading}>
        + Добавить адрес
      </Button>
    </div>

    {#if loading}
      <div class="flex justify-center py-8">
        <Spinner size="lg" />
      </div>
    {:else if addresses.length === 0}
      <div class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <span class="text-2xl">📍</span>
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Нет адресов</h3>
        <p class="text-gray-600 mb-4">Добавьте адрес для доставки ваших заказов</p>
        <Button on:click={openAddModal}>Добавить первый адрес</Button>
      </div>
    {:else}
      <div class="grid gap-4">
        {#each addresses as address (address.id)}
          <div class="border border-gray-200 rounded-lg p-4 relative">
            {#if address.isDefault}
              <div class="absolute top-2 right-2">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  По умолчанию
                </span>
              </div>
            {/if}

            <div class="space-y-2">
              <div class="font-medium text-gray-900">
                {address.fullAddress}
              </div>
              
              <div class="text-sm text-gray-600">
                {address.city}{address.postalCode ? `, ${address.postalCode}` : ''}
                {address.country ? `, ${address.country}` : ''}
              </div>
              
              {#if address.addressComments}
                <div class="text-sm text-gray-500 italic">
                  {address.addressComments}
                </div>
              {/if}
            </div>

            <div class="flex items-center justify-between mt-4">
              <div class="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  on:click={() => openEditModal(address)}
                >
                  Редактировать
                </Button>
                
                {#if !address.isDefault}
                  <Button
                    variant="outline"
                    size="sm"
                    on:click={() => setDefaultAddress(address)}
                  >
                    Сделать основным
                  </Button>
                {/if}
              </div>

              {#if addresses.length > 1}
                <Button
                  variant="outline"
                  size="sm"
                  on:click={() => deleteAddress(address.id)}
                  disabled={deletingAddressId === address.id}
                  className="text-red-600 border-red-300 hover:bg-red-50"
                >
                  {#if deletingAddressId === address.id}
                    <Spinner size="sm" />
                  {:else}
                    Удалить
                  {/if}
                </Button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</Card>

<!-- Add/Edit Address Modal -->
<Modal bind:open={showAddModal} title={editingAddress ? 'Редактировать адрес' : 'Добавить адрес'}>
  <form on:submit|preventDefault={saveAddress} class="space-y-4">
    <div>
      <label for="fullAddress" class="block text-sm font-medium text-gray-700 mb-1">
        Полный адрес *
      </label>
      <Input
        id="fullAddress"
        bind:value={addressForm.fullAddress}
        placeholder="ул. Примерная, д. 123, кв. 45"
        disabled={savingAddress}
        error={errors.fullAddress}
        required
      />
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label for="city" class="block text-sm font-medium text-gray-700 mb-1">
          Город *
        </label>
        <Input
          id="city"
          bind:value={addressForm.city}
          placeholder="Москва"
          disabled={savingAddress}
          error={errors.city}
          required
        />
      </div>

      <div>
        <label for="postalCode" class="block text-sm font-medium text-gray-700 mb-1">
          Почтовый индекс
        </label>
        <Input
          id="postalCode"
          bind:value={addressForm.postalCode}
          placeholder="123456"
          disabled={savingAddress}
          error={errors.postalCode}
        />
      </div>
    </div>

    <div>
      <label for="country" class="block text-sm font-medium text-gray-700 mb-1">
        Страна
      </label>
      <Input
        id="country"
        bind:value={addressForm.country}
        placeholder="Россия"
        disabled={savingAddress}
        error={errors.country}
      />
    </div>

    <div>
      <label for="addressComments" class="block text-sm font-medium text-gray-700 mb-1">
        Комментарии к адресу
      </label>
      <textarea
        id="addressComments"
        bind:value={addressForm.addressComments}
        placeholder="Дополнительная информация об адресе..."
        disabled={savingAddress}
        rows="3"
        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
      ></textarea>
    </div>

    <div class="flex items-center">
      <input
        id="isDefault"
        type="checkbox"
        bind:checked={addressForm.isDefault}
        disabled={savingAddress}
        class="h-4 w-4 text-pink-600 focus:ring-pink-500 border-gray-300 rounded"
      />
      <label for="isDefault" class="ml-2 text-sm text-gray-700">
        Сделать адресом по умолчанию
      </label>
    </div>

    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
      <Button
        variant="outline"
        on:click={() => showAddModal = false}
        disabled={savingAddress}
      >
        Отмена
      </Button>
      
      <Button
        type="submit"
        disabled={savingAddress}
        className="min-w-[120px]"
      >
        {#if savingAddress}
          <Spinner size="sm" className="mr-2" />
        {/if}
        {editingAddress ? 'Обновить' : 'Добавить'}
      </Button>
    </div>
  </form>
</Modal>