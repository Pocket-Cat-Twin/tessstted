<script lang="ts">
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';
  import { 
    validateLoginForm, 
    validateField,
    detectAuthMethod,
    applyPhoneMask,
    type AuthMethod
  } from '$lib/utils/validation-enhanced';

  let loginMethod: AuthMethod = 'email';
  let loginContact = '';
  let password = '';
  let error = '';
  let loading = false;
  let fieldErrors: Record<string, string> = {};
  let autoDetect = true; // Auto-detect login method from input

  $: user = $authStore.user;

  // Redirect if already logged in
  $: if (user) {
    goto('/');
  }

  // Auto-detect login method when typing
  $: if (autoDetect && loginContact) {
    const detected = detectAuthMethod(loginContact);
    if (detected !== 'unknown' && detected !== loginMethod) {
      loginMethod = detected;
    }
  }

  // Handle login method change
  function handleMethodChange(method: AuthMethod) {
    loginMethod = method;
    autoDetect = false;
    loginContact = '';
    fieldErrors = {};
    error = '';
  }

  // Handle phone input masking
  function handlePhoneInput(event: Event) {
    const target = event.target as HTMLInputElement;
    const cursorPosition = target.selectionStart;
    
    if (loginMethod === 'phone') {
      const masked = applyPhoneMask(target.value);
      loginContact = masked;
      
      // Restore cursor position
      setTimeout(() => {
        target.setSelectionRange(cursorPosition, cursorPosition);
      }, 0);
    }
  }

  // Real-time validation
  function validateFormField(field: string, value: string) {
    const validation = validateField(field, value, undefined, true);
    if (!validation.isValid && validation.error) {
      fieldErrors[field] = validation.error;
    } else {
      delete fieldErrors[field];
    }
    fieldErrors = { ...fieldErrors };
  }

  async function handleSubmit() {
    // Clear previous errors
    error = '';
    fieldErrors = {};

    // Validate form
    const validation = validateLoginForm(loginMethod, loginContact, password);
    if (!validation.isValid) {
      error = validation.errors.join('. ');
      return;
    }

    loading = true;

    try {
      // Prepare login data
      const loginData: any = {
        loginMethod,
        password,
      };

      if (loginMethod === 'email') {
        loginData.email = loginContact;
      } else {
        loginData.phone = loginContact;
      }

      const result = await authStore.login(loginData);
      
      if (result.success) {
        goto('/');
      } else {
        error = result.message || 'Ошибка входа';
      }
    } catch (err) {
      error = 'Ошибка подключения к серверу';
    } finally {
      loading = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSubmit();
    }
  }
</script>

<svelte:head>
  <title>Вход - YuYu Lolita Shopping</title>
  <meta name="description" content="Войдите в свой аккаунт YuYu Lolita Shopping" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-md w-full space-y-8">
    <!-- Header -->
    <div class="text-center">
      <div class="flex justify-center">
        <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center">
          <span class="text-white font-bold text-xl">Y</span>
        </div>
      </div>
      <h2 class="mt-6 text-3xl font-bold text-gray-900">
        Вход в аккаунт
      </h2>
      <p class="mt-2 text-sm text-gray-600">
        Ты мечтаешь — мы исполняем
      </p>
      <p class="mt-2 text-sm text-gray-600">
        Или 
        <a href="/register" class="font-medium text-primary-600 hover:text-primary-500 transition-colors">
          создайте новый аккаунт
        </a>
      </p>
    </div>

    <!-- Login Method Selection -->
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <h3 class="text-sm font-medium text-gray-900 mb-3">Способ входа</h3>
      <div class="grid grid-cols-2 gap-3">
        <button
          type="button"
          class="flex items-center justify-center px-4 py-2 border rounded-md text-sm font-medium transition-colors {loginMethod === 'email' ? 'bg-primary-50 border-primary-500 text-primary-700' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}"
          on:click={() => handleMethodChange('email')}
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Email
        </button>
        <button
          type="button"
          class="flex items-center justify-center px-4 py-2 border rounded-md text-sm font-medium transition-colors {loginMethod === 'phone' ? 'bg-primary-50 border-primary-500 text-primary-700' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}"
          on:click={() => handleMethodChange('phone')}
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
          Телефон
        </button>
      </div>
      {#if autoDetect}
        <p class="text-xs text-gray-500 mt-2 text-center">
          💡 Система автоматически определит способ входа при вводе
        </p>
      {/if}
    </div>

    <!-- Form -->
    <form class="mt-8 space-y-6" on:submit|preventDefault={handleSubmit}>
      <div class="space-y-4">
        <!-- Contact Input (Email or Phone) -->
        {#if loginMethod === 'email'}
          <Input
            id="email"
            name="email"
            type="email"
            label="Email адрес"
            placeholder="Введите ваш email"
            bind:value={loginContact}
            required
            autocomplete="email"
            disabled={loading}
            error={fieldErrors.email}
            on:keydown={handleKeydown}
            on:blur={() => validateFormField('email', loginContact)}
          />
        {:else}
          <Input
            id="phone"
            name="phone"
            type="tel"
            label="Номер телефона"
            placeholder="+7 (999) 123-45-67"
            bind:value={loginContact}
            required
            autocomplete="tel"
            disabled={loading}
            error={fieldErrors.phone}
            on:keydown={handleKeydown}
            on:input={handlePhoneInput}
            on:blur={() => validateFormField('phone', loginContact)}
          />
        {/if}

        <!-- Password -->
        <Input
          id="password"
          name="password"
          type="password"
          label="Пароль"
          placeholder="Введите ваш пароль"
          bind:value={password}
          required
          autocomplete="current-password"
          disabled={loading}
          error={fieldErrors.password}
          on:keydown={handleKeydown}
          on:blur={() => validateFormField('password', password)}
        />
      </div>

      <!-- Error message -->
      {#if error}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      {/if}

      <!-- Forgot password link -->
      <div class="text-right">
        <a 
          href="/forgot-password" 
          class="text-sm text-primary-600 hover:text-primary-500 transition-colors"
        >
          Забыли пароль?
        </a>
      </div>

      <!-- Submit button -->
      <Button
        type="submit"
        variant="primary"
        size="lg"
        fullWidth
        {loading}
        disabled={loading || !loginContact || !password}
      >
        {loading ? 'Вход...' : 'Войти'}
      </Button>
    </form>

    <!-- Social login (placeholder) -->
    <div class="mt-6">
      <div class="relative">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-gray-300" />
        </div>
        <div class="relative flex justify-center text-sm">
          <span class="px-2 bg-gray-50 text-gray-500">Или войдите через</span>
        </div>
      </div>

      <div class="mt-6 grid grid-cols-2 gap-3">
        <!-- VK -->
        <Button variant="outline" fullWidth disabled>
          <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12.785 16.241s.288-.032.436-.194c.136-.148.131-.425.131-.425s-.019-1.299.582-1.491c.593-.189 1.354 1.256 2.161 1.81.612.419 1.078.327 1.078.327l2.164-.03s1.132-.071.595-.961c-.044-.073-.312-.658-1.608-1.859-1.357-1.257-1.175-1.053.459-3.224.995-1.32 1.393-2.126 1.268-2.472-.119-.329-.852-.242-.852-.242l-2.436.015s-.18-.025-.314.055c-.131.078-.215.26-.215.26s-.387 1.03-.902 1.906c-1.085 1.849-1.517 1.947-1.694 1.831-.41-.267-.308-1.073-.308-1.646 0-1.793.272-2.542-.53-2.732-.266-.063-.462-.105-1.142-.112-.873-.009-1.613.003-2.033.208-.28.136-.496.44-.364.458.163.022.533.1.729.368.253.346.244 1.122.244 1.122s.146 2.111-.34 2.373c-.334.18-.792-.187-1.775-1.856-.503-.859-.883-1.81-.883-1.81s-.073-.179-.203-.275c-.158-.117-.379-.154-.379-.154l-2.315.015s-.348.01-.475.161c-.113.134-.009.41-.009.41s1.816 4.25 3.873 6.396c1.885 1.969 4.025 1.84 4.025 1.84z"/>
          </svg>
          VK
        </Button>

        <!-- Telegram -->
        <Button variant="outline" fullWidth disabled>
          <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.13-.31-1.09-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
          Telegram
        </Button>
      </div>
    </div>

    <!-- Footer links -->
    <div class="text-center space-y-2">
      <p class="text-xs text-gray-500">
        🔒 Ваши данные защищены и не передаются третьим лицам
      </p>
      <div class="flex justify-center space-x-4 text-xs">
        <a href="/terms" class="text-primary-600 hover:text-primary-500 transition-colors">
          Условиями использования
        </a>
        <a href="/privacy" class="text-primary-600 hover:text-primary-500 transition-colors">
          Политикой конфиденциальности
        </a>
      </div>
    </div>
  </div>
</div>