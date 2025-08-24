<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { authStore } from '$lib/stores/auth';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';
  import { 
    validateLoginForm, 
    normalizePhoneNumber,
    applyPhoneMask,
    detectAuthMethod,
    createFormValidator,
    type AuthMethod
  } from '$lib/utils/validation-enhanced';

  // Form state
  let loginMethod: AuthMethod = 'email';
  let emailOrPhone = '';
  let password = '';
  let autoDetectMethod = true;

  // UI state
  let error = '';
  let loading = false;
  let rememberMe = false;

  // Form validator
  const validator = createFormValidator();
  $: fieldErrors = validator.getErrors();

  $: user = $authStore.user;

  // Get success message from URL params
  $: successMessage = $page.url.searchParams.get('message');

  // Redirect if already logged in
  $: if (user) {
    goto('/');
  }

  // Auto-detect authentication method from input
  function handleContactInput(event: Event) {
    const target = event.target as HTMLInputElement;
    const value = target.value;
    
    if (autoDetectMethod) {
      const detectedMethod = detectAuthMethod(value);
      if (detectedMethod !== 'unknown') {
        loginMethod = detectedMethod;
      }
    }
    
    // Apply phone masking if needed
    if (loginMethod === 'phone') {
      const cursorPosition = target.selectionStart;
      const masked = applyPhoneMask(value);
      emailOrPhone = masked;
      
      // Restore cursor position
      setTimeout(() => {
        target.setSelectionRange(cursorPosition, cursorPosition);
      }, 0);
    } else {
      emailOrPhone = value;
    }

    // Real-time validation
    validateEmailOrPhone();
  }

  // Handle manual method selection
  function handleMethodChange(method: AuthMethod) {
    loginMethod = method;
    autoDetectMethod = false;
    emailOrPhone = '';
    validator.clearAllErrors();
    error = '';
  }

  // Real-time validation for email/phone
  function validateEmailOrPhone() {
    const field = loginMethod === 'email' ? 'email' : 'phone';
    validator.validate(field, emailOrPhone, undefined, true);
  }

  // Form validation
  function validateFormField(field: string, value: string) {
    validator.validate(field, value, undefined, true);
  }

  // Form submission
  async function handleSubmit() {
    error = '';
    validator.clearAllErrors();

    // Validate form
    const validation = validateLoginForm(loginMethod, emailOrPhone, password);
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
        loginData.email = emailOrPhone;
      } else {
        loginData.phone = normalizePhoneNumber(emailOrPhone);
      }

      const result = await authStore.login(
        loginMethod === 'email' ? emailOrPhone : normalizePhoneNumber(emailOrPhone), 
        password
      );
      
      if (result.success) {
        // Handle remember me
        if (rememberMe) {
          localStorage.setItem('rememberedAuth', JSON.stringify({
            method: loginMethod,
            contact: emailOrPhone
          }));
        } else {
          localStorage.removeItem('rememberedAuth');
        }

        goto('/');
      } else {
        error = result.message || 'Ошибка входа';
      }
    } catch (err) {
      console.error('Login error:', err);
      error = 'Ошибка подключения к серверу';
    } finally {
      loading = false;
    }
  }

  // Load remembered authentication data
  function loadRememberedAuth() {
    try {
      const remembered = localStorage.getItem('rememberedAuth');
      if (remembered) {
        const data = JSON.parse(remembered);
        loginMethod = data.method;
        emailOrPhone = data.contact;
        rememberMe = true;
        autoDetectMethod = false;
      }
    } catch (err) {
      console.error('Failed to load remembered auth:', err);
    }
  }

  // Initialize
  import { onMount } from 'svelte';
  onMount(() => {
    loadRememberedAuth();
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSubmit();
    }
  }
</script>

<svelte:head>
  <title>Вход - LolitaFashion.su</title>
  <meta name="description" content="Войдите в аккаунт LolitaFashion.su для управления заказами" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-md w-full space-y-8">
    <!-- Header -->
    <div class="text-center">
      <div class="flex justify-center">
        <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center">
          <span class="text-white font-bold text-xl">L</span>
        </div>
      </div>
      <h2 class="mt-6 text-3xl font-bold text-gray-900">
        Вход в аккаунт
      </h2>
      <p class="mt-2 text-sm text-gray-600">
        Добро пожаловать в мир лолита-моды
      </p>
      <p class="mt-2 text-sm text-gray-600">
        Или 
        <a href="/register" class="font-medium text-primary-600 hover:text-primary-500 transition-colors">
          создайте новый аккаунт
        </a>
      </p>
    </div>

    <!-- Success message -->
    {#if successMessage}
      <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
        {successMessage}
      </div>
    {/if}

    <!-- Login Method Selection (when auto-detect is disabled) -->
    {#if !autoDetectMethod}
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
        <button
          type="button"
          class="mt-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          on:click={() => {autoDetectMethod = true; emailOrPhone = '';}}
        >
          Включить автоопределение
        </button>
      </div>
    {/if}

    <!-- Form -->
    <form class="mt-8 space-y-6" on:submit|preventDefault={handleSubmit}>
      <div class="space-y-4">
        <!-- Email or Phone -->
        <div>
          {#if loginMethod === 'email'}
            <Input
              id="email"
              name="email"
              type="email"
              label="Email адрес"
              placeholder="Введите ваш email"
              bind:value={emailOrPhone}
              required
              autocomplete="email"
              disabled={loading}
              error={fieldErrors.email}
              on:keydown={handleKeydown}
              on:input={handleContactInput}
              on:blur={validateEmailOrPhone}
            />
          {:else}
            <Input
              id="phone"
              name="phone"
              type="tel"
              label="Номер телефона"
              placeholder="+7 (999) 123-45-67"
              bind:value={emailOrPhone}
              required
              autocomplete="tel"
              disabled={loading}
              error={fieldErrors.phone}
              on:keydown={handleKeydown}
              on:input={handleContactInput}
              on:blur={validateEmailOrPhone}
            />
          {/if}
          
          <!-- Auto-detect helper -->
          {#if autoDetectMethod && emailOrPhone}
            <div class="mt-1 text-xs text-gray-500">
              Определен способ входа: 
              <span class="font-medium">
                {loginMethod === 'email' ? 'Email' : 'Телефон'}
              </span>
              <button
                type="button"
                class="ml-2 text-primary-600 hover:text-primary-500"
                on:click={() => autoDetectMethod = false}
              >
                Изменить
              </button>
            </div>
          {/if}
        </div>

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

      <!-- Options row -->
      <div class="flex items-center justify-between">
        <!-- Remember me -->
        <label class="flex items-center">
          <input
            type="checkbox"
            bind:checked={rememberMe}
            class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            disabled={loading}
          />
          <span class="ml-2 text-sm text-gray-600">Запомнить меня</span>
        </label>

        <!-- Forgot password link -->
        <a 
          href="/forgot-password" 
          class="text-sm text-primary-600 hover:text-primary-500 transition-colors"
        >
          Забыли пароль?
        </a>
      </div>

      <!-- Error message -->
      {#if error}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      {/if}

      <!-- Submit button -->
      <Button
        type="submit"
        variant="primary"
        size="lg"
        fullWidth
        {loading}
        disabled={loading || !emailOrPhone || !password}
      >
        {loading ? 'Вход...' : 'Войти'}
      </Button>
    </form>

    <!-- Social login -->
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

    <!-- Help -->
    <div class="text-center space-y-2">
      <p class="text-xs text-gray-500">
        Возникли проблемы с входом?
      </p>
      <div class="flex justify-center space-x-4 text-xs">
        <a href="/help/login" class="text-primary-600 hover:text-primary-500 transition-colors">
          Помощь
        </a>
        <a href="/contact" class="text-primary-600 hover:text-primary-500 transition-colors">
          Связаться с нами
        </a>
      </div>
    </div>
  </div>
</div>