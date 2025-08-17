<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Input from '$lib/components/ui/Input.svelte';
  import { validateSMSCode, createFormValidator } from '$lib/utils/validation-enhanced';
  import { api } from '$lib/api/client-simple';

  // Form state
  let verificationCode = '';
  let token = '';

  // UI state
  let error = '';
  let success = '';
  let loading = false;
  let resendLoading = false;
  let resendCooldown = 0;
  let attempts = 0;
  let maxAttempts = 3;

  // Timer
  let cooldownTimer: number;

  // Form validator
  const validator = createFormValidator();
  $: fieldErrors = validator.getErrors();

  // Get message and token from URL params
  $: message = $page.url.searchParams.get('message');
  $: urlToken = $page.url.searchParams.get('token');

  onMount(() => {
    // Get token from URL or localStorage
    token = urlToken || localStorage.getItem('phoneVerificationToken') || '';
    
    if (!token) {
      error = 'Токен верификации не найден. Пожалуйста, повторите регистрацию.';
    }

    // Start resend cooldown (60 seconds)
    startResendCooldown();
  });

  function startResendCooldown() {
    resendCooldown = 60;
    cooldownTimer = setInterval(() => {
      resendCooldown--;
      if (resendCooldown <= 0) {
        clearInterval(cooldownTimer);
      }
    }, 1000);
  }

  // Real-time validation for SMS code
  function validateCode() {
    validator.validate('smsCode', verificationCode);
  }

  // Handle code input (auto-submit when complete)
  function handleCodeInput(event: Event) {
    const target = event.target as HTMLInputElement;
    let value = target.value.replace(/\D/g, ''); // Only digits
    
    if (value.length > 6) {
      value = value.slice(0, 6);
    }
    
    verificationCode = value;
    
    // Auto-submit when 6 digits entered
    if (value.length === 6) {
      setTimeout(() => handleSubmit(), 100);
    }
    
    validateCode();
  }

  // Form submission
  async function handleSubmit() {
    error = '';
    success = '';
    validator.clearAllErrors();

    // Validate SMS code
    const codeValidation = validateSMSCode(verificationCode);
    if (!codeValidation.isValid) {
      error = codeValidation.error || 'Некорректный код';
      return;
    }

    if (!token) {
      error = 'Токен верификации отсутствует';
      return;
    }

    loading = true;

    try {
      const response = await api.verifyPhone({
        token,
        code: verificationCode
      });
      
      if (response.success) {
        success = response.message || 'Телефон успешно подтвержден!';
        
        // Clear stored token
        localStorage.removeItem('phoneVerificationToken');
        
        // Redirect to login after delay
        setTimeout(() => {
          goto('/login?message=' + encodeURIComponent('Регистрация завершена! Войдите в систему'));
        }, 2000);
      } else {
        attempts++;
        error = response.message || 'Неверный код подтверждения';
        
        if (attempts >= maxAttempts) {
          error = 'Превышено максимальное количество попыток. Запросите новый код.';
        }
      }
    } catch (err) {
      console.error('Phone verification error:', err);
      error = 'Ошибка подключения к серверу';
    } finally {
      loading = false;
    }
  }

  // Resend SMS
  async function handleResendSMS() {
    if (resendCooldown > 0) return;
    
    resendLoading = true;
    error = '';

    try {
      const response = await api.resendPhoneVerification({ token });
      
      if (response.success) {
        success = 'SMS с новым кодом отправлен';
        attempts = 0; // Reset attempts
        startResendCooldown();
        verificationCode = '';
      } else {
        error = response.message || 'Ошибка отправки SMS';
      }
    } catch (err) {
      console.error('Resend SMS error:', err);
      error = 'Ошибка подключения к серверу';
    } finally {
      resendLoading = false;
    }
  }

  // Handle paste
  function handlePaste(event: ClipboardEvent) {
    event.preventDefault();
    const pastedText = event.clipboardData?.getData('text') || '';
    const digits = pastedText.replace(/\D/g, '').slice(0, 6);
    
    if (digits.length === 6) {
      verificationCode = digits;
      validateCode();
      setTimeout(() => handleSubmit(), 100);
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSubmit();
    }
  }

  // Cleanup timer on destroy
  import { onDestroy } from 'svelte';
  onDestroy(() => {
    if (cooldownTimer) {
      clearInterval(cooldownTimer);
    }
  });
</script>

<svelte:head>
  <title>Подтверждение телефона - LolitaFashion.su</title>
  <meta name="description" content="Подтвердите номер телефона для завершения регистрации" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-md w-full space-y-8">
    <!-- Header -->
    <div class="text-center">
      <div class="flex justify-center">
        <div class="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full flex items-center justify-center">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
      </div>
      <h2 class="mt-6 text-3xl font-bold text-gray-900">
        Подтверждение телефона
      </h2>
      <p class="mt-2 text-sm text-gray-600 max-w-sm mx-auto">
        Мы отправили SMS с 6-значным кодом на ваш номер телефона. Введите его ниже для завершения регистрации.
      </p>
    </div>

    <!-- Info message -->
    {#if message}
      <div class="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg text-sm">
        {message}
      </div>
    {/if}

    <!-- Success message -->
    {#if success}
      <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
        <div class="flex items-center">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          {success}
        </div>
        <div class="mt-2 text-xs">
          Перенаправляем на страницу входа...
        </div>
      </div>
    {/if}

    <!-- Form -->
    {#if !success}
      <form class="mt-8 space-y-6" on:submit|preventDefault={handleSubmit}>
        <div class="space-y-4">
          <!-- SMS Code Input -->
          <div>
            <label for="code" class="block text-sm font-medium text-gray-700 mb-2">
              Код подтверждения
            </label>
            <Input
              id="code"
              name="code"
              type="text"
              inputmode="numeric"
              pattern="[0-9]*"
              placeholder="000000"
              bind:value={verificationCode}
              required
              autocomplete="one-time-code"
              disabled={loading}
              error={fieldErrors.smsCode}
              maxlength={6}
              class="text-center text-2xl tracking-widest font-mono"
              on:input={handleCodeInput}
              on:paste={handlePaste}
              on:keydown={handleKeydown}
            />
            <div class="mt-1 text-xs text-gray-500 text-center">
              Введите 6 цифр из SMS
            </div>
            
            <!-- Attempts counter -->
            {#if attempts > 0}
              <div class="mt-2 text-xs text-center {attempts >= maxAttempts ? 'text-red-600' : 'text-yellow-600'}">
                Попытка {attempts} из {maxAttempts}
              </div>
            {/if}
          </div>
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
          disabled={loading || verificationCode.length !== 6}
        >
          {loading ? 'Проверка...' : 'Подтвердить код'}
        </Button>
      </form>

      <!-- Resend SMS -->
      <div class="text-center space-y-4">
        <div class="text-sm text-gray-600">
          Не получили SMS?
        </div>
        
        {#if resendCooldown > 0}
          <div class="text-sm text-gray-500">
            Повторная отправка доступна через {resendCooldown} сек.
          </div>
        {:else}
          <Button
            variant="outline"
            on:click={handleResendSMS}
            disabled={resendLoading}
            loading={resendLoading}
          >
            {resendLoading ? 'Отправка...' : 'Отправить код заново'}
          </Button>
        {/if}
      </div>

      <!-- Help -->
      <div class="border-t border-gray-200 pt-6">
        <div class="text-center space-y-3">
          <p class="text-xs text-gray-500">
            Проблемы с получением SMS?
          </p>
          <div class="flex justify-center space-x-4 text-xs">
            <a href="/help/sms" class="text-primary-600 hover:text-primary-500 transition-colors">
              Помощь
            </a>
            <a href="/contact" class="text-primary-600 hover:text-primary-500 transition-colors">
              Связаться с поддержкой
            </a>
          </div>
          <div class="mt-4">
            <a href="/register" class="text-xs text-gray-500 hover:text-gray-700 transition-colors">
              ← Вернуться к регистрации
            </a>
          </div>
        </div>
      </div>
    {/if}

    <!-- Technical info (for development) -->
    {#if process.env.NODE_ENV === 'development' && token}
      <div class="bg-gray-100 p-3 rounded text-xs text-gray-600">
        <div class="font-mono break-all">Token: {token}</div>
      </div>
    {/if}
  </div>
</div>

<style>
  /* Enhanced input styling for SMS code */
  :global(.sms-code-input) {
    letter-spacing: 0.5rem;
    text-align: center;
  }
</style>