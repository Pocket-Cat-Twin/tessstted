<script lang="ts">
  import { onMount } from 'svelte';
  import { configStore, configActions } from '$lib/stores/config';
  import Button from '$lib/components/ui/Button.svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import type { FAQ } from '@lolita-fashion/shared';

  let faqs: FAQ[] = [];
  let loading = true;
  let error = '';
  let expandedFaq: string | null = null;

  onMount(async () => {
    await loadFaqs();
  });

  async function loadFaqs() {
    loading = true;
    error = '';
    
    try {
      const response = await fetch('http://127.0.0.1:3001/config/faq');
      const data = await response.json();
      
      if (data.success) {
        faqs = data.data.faqs;
      } else {
        error = 'Не удалось загрузить FAQ';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Ошибка загрузки FAQ';
    } finally {
      loading = false;
    }
  }

  function toggleFaq(faqId: string) {
    expandedFaq = expandedFaq === faqId ? null : faqId;
  }

  function formatAnswer(answer: string) {
    // Simple formatting for line breaks
    return answer.replace(/\n/g, '<br>');
  }
</script>

<svelte:head>
  <title>Часто задаваемые вопросы - YuYu Lolita</title>
  <meta name="description" content="Ответы на часто задаваемые вопросы о заказах, доставке и услугах YuYu Lolita" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 to-purple-50">
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Часто задаваемые <span class="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600">вопросы</span>
      </h1>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto">
        Найдите ответы на наиболее популярные вопросы о наших услугах и заказах
      </p>
    </div>

    {#if loading}
      <!-- Loading state -->
      <div class="flex justify-center items-center py-12">
        <Spinner size="large" />
      </div>
    {:else if error}
      <!-- Error state -->
      <div class="text-center py-12">
        <div class="bg-red-50 border border-red-200 rounded-lg p-8 max-w-md mx-auto">
          <div class="text-red-600 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-red-800 mb-2">Ошибка загрузки</h3>
          <p class="text-red-600 mb-4">{error}</p>
          <Button variant="secondary" on:click={loadFaqs}>
            Попробовать снова
          </Button>
        </div>
      </div>
    {:else if faqs.length === 0}
      <!-- Empty state -->
      <div class="text-center py-12">
        <div class="text-gray-400 mb-4">
          <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 class="text-xl font-medium text-gray-900 mb-2">Пока нет вопросов</h3>
        <p class="text-gray-600">Скоро здесь появятся ответы на популярные вопросы!</p>
      </div>
    {:else}
      <!-- FAQ List -->
      <div class="max-w-4xl mx-auto">
        <div class="space-y-4">
          {#each faqs as faq}
            <Card class="overflow-hidden transition-all duration-300 hover:shadow-lg">
              <button
                class="w-full p-6 text-left focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-inset"
                on:click={() => toggleFaq(faq.id)}
              >
                <div class="flex items-center justify-between">
                  <h3 class="text-lg font-semibold text-gray-900 pr-4">
                    {faq.question}
                  </h3>
                  <div class="flex-shrink-0 ml-4">
                    <svg 
                      class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedFaq === faq.id ? 'rotate-180' : ''}"
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </button>
              
              {#if expandedFaq === faq.id}
                <div class="px-6 pb-6 pt-0">
                  <div class="border-t border-gray-200 pt-4">
                    <div class="text-gray-700 leading-relaxed">
                      {@html formatAnswer(faq.answer)}
                    </div>
                  </div>
                </div>
              {/if}
            </Card>
          {/each}
        </div>

        <!-- Contact section -->
        <div class="mt-16 text-center">
          <Card class="bg-gradient-to-r from-pink-50 to-purple-50 border-pink-200">
            <div class="p-8">
              <h3 class="text-2xl font-bold text-gray-900 mb-4">
                Не нашли ответ на свой вопрос?
              </h3>
              <p class="text-gray-600 mb-6">
                Свяжитесь с нами, и мы поможем вам с любыми вопросами
              </p>
              
              <div class="flex flex-col sm:flex-row gap-4 justify-center">
                {#if $configStore.config.contact_email}
                  <Button 
                    variant="primary" 
                    size="lg"
                    on:click={() => window.location.href = `mailto:${$configStore.config.contact_email}`}
                  >
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 7.89a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Написать на почту
                  </Button>
                {/if}
                
                {#if $configStore.config.telegram_link}
                  <Button 
                    variant="outline" 
                    size="lg"
                    on:click={() => window.open($configStore.config.telegram_link, '_blank')}
                  >
                    <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                    </svg>
                    Telegram
                  </Button>
                {/if}
              </div>
            </div>
          </Card>
        </div>
      </div>
    {/if}
  </div>
</div>