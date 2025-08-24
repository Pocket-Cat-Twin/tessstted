<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Card, Button, Input, Spinner } from '$lib/components/ui';
  import { api } from '$lib/api/client-simple';

  // Props
  export let profile: any = null;
  export let loading = false;

  // Form data
  let formData = {
    name: profile?.user?.name || '',
    fullName: profile?.fullName || '',
    contactPhone: profile?.contactPhone || '',
    contactEmail: profile?.contactEmail || '',
    avatar: profile?.avatar || '',
  };

  // State
  let saving = false;
  let errors: Record<string, string> = {};

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Update form data when profile changes
  $: if (profile) {
    formData = {
      name: profile.user?.name || '',
      fullName: profile.fullName || '',
      contactPhone: profile.contactPhone || '',
      contactEmail: profile.contactEmail || '',
      avatar: profile.avatar || '',
    };
  }

  // Validation
  function validateForm() {
    errors = {};
    
    if (!formData.name.trim()) {
      errors.name = 'Имя обязательно для заполнения';
    }
    
    if (formData.contactEmail && !isValidEmail(formData.contactEmail)) {
      errors.contactEmail = 'Неверный формат email';
    }
    
    if (formData.contactPhone && !isValidPhone(formData.contactPhone)) {
      errors.contactPhone = 'Неверный формат телефона';
    }

    return Object.keys(errors).length === 0;
  }

  function isValidEmail(email: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function isValidPhone(phone: string) {
    return /^[+]?[1-9][\d]{0,15}$/.test(phone.replace(/\s/g, ''));
  }

  // Handle form submission
  async function handleSubmit() {
    if (!validateForm()) return;

    saving = true;
    
    try {
      const response = await api.updateProfile(formData);
      
      if (response.success) {
        dispatch('success', { message: 'Профиль успешно обновлен' });
      } else {
        dispatch('error', { message: response.message || 'Ошибка при обновлении профиля' });
      }
    } catch (_error) {
      dispatch('error', { message: 'Ошибка подключения к серверу' });
    } finally {
      saving = false;
    }
  }

  // Handle avatar file upload
  function handleAvatarChange(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    
    if (file) {
      // For now, just show the file name
      // In a real app, you'd upload the file and get a URL
      formData.avatar = file.name;
    }
  }
</script>

<Card variant="bordered" class="max-w-2xl mx-auto">
  <div class="space-y-6">
    <div class="flex items-center space-x-4 pb-4 border-b border-gray-200">
      <div class="w-16 h-16 bg-gradient-to-br from-pink-100 to-purple-100 rounded-full flex items-center justify-center">
        {#if formData.avatar}
          <img src={formData.avatar} alt="Аватар" class="w-16 h-16 rounded-full object-cover">
        {:else}
          <span class="text-2xl text-pink-600">
            {formData.name.charAt(0).toUpperCase() || '👤'}
          </span>
        {/if}
      </div>
      <div>
        <h2 class="text-xl font-semibold text-gray-900">Редактировать профиль</h2>
        <p class="text-sm text-gray-600">Обновите свою персональную информацию</p>
      </div>
    </div>

    <form on:submit|preventDefault={handleSubmit} class="space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="name" class="block text-sm font-medium text-gray-700 mb-1">
            Имя *
          </label>
          <Input
            id="name"
            bind:value={formData.name}
            placeholder="Введите ваше имя"
            disabled={saving || loading}
            error={errors.name}
            required
          />
        </div>

        <div>
          <label for="fullName" class="block text-sm font-medium text-gray-700 mb-1">
            Полное имя
          </label>
          <Input
            id="fullName"
            bind:value={formData.fullName}
            placeholder="Введите полное имя"
            disabled={saving || loading}
            error={errors.fullName}
          />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="contactEmail" class="block text-sm font-medium text-gray-700 mb-1">
            Контактный email
          </label>
          <Input
            id="contactEmail"
            type="email"
            bind:value={formData.contactEmail}
            placeholder="contact@example.com"
            disabled={saving || loading}
            error={errors.contactEmail}
          />
        </div>

        <div>
          <label for="contactPhone" class="block text-sm font-medium text-gray-700 mb-1">
            Контактный телефон
          </label>
          <Input
            id="contactPhone"
            type="tel"
            bind:value={formData.contactPhone}
            placeholder="+7 (999) 123-45-67"
            disabled={saving || loading}
            error={errors.contactPhone}
          />
        </div>
      </div>

      <div>
        <label for="avatar" class="block text-sm font-medium text-gray-700 mb-1">
          Аватар
        </label>
        <input
          id="avatar"
          type="file"
          accept="image/*"
          on:change={handleAvatarChange}
          disabled={saving || loading}
          class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-pink-50 file:text-pink-600 hover:file:bg-pink-100 disabled:opacity-50"
        />
        <p class="text-xs text-gray-500 mt-1">PNG, JPG до 5MB</p>
      </div>

      <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <Button
          variant="outline"
          on:click={() => dispatch('cancel')}
          disabled={saving || loading}
        >
          Отмена
        </Button>
        
        <Button
          type="submit"
          disabled={saving || loading}
          class="min-w-[120px]"
        >
          {#if saving}
            <Spinner size="sm" className="mr-2" />
          {/if}
          Сохранить
        </Button>
      </div>
    </form>
  </div>
</Card>

<style>
  input[type="file"]::-webkit-file-upload-button {
    visibility: hidden;
  }
</style>