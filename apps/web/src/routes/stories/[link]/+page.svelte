<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { storiesActions } from '$lib/stores/stories';
  import { formatDate } from '$lib/utils/date';
  import Button from '$lib/components/ui/Button.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import type { Story } from '@yuyu/shared';

  let story: Story | null = null;
  let loading = true;
  let error = '';

  $: link = $page.params.link;

  onMount(async () => {
    await loadStory();
  });

  async function loadStory() {
    loading = true;
    error = '';
    
    try {
      story = await storiesActions.loadStory(link);
      if (!story) {
        error = 'История не найдена';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Ошибка загрузки истории';
    } finally {
      loading = false;
    }
  }

  function getThumbnailUrl(thumbnail: string | null) {
    if (!thumbnail) return '/images/story-default.jpg';
    return thumbnail.startsWith('http') ? thumbnail : `/uploads/${thumbnail}`;
  }

  function getImageUrl(imagePath: string) {
    return imagePath.startsWith('http') ? imagePath : `/uploads/${imagePath}`;
  }

  function goBack() {
    goto('/stories');
  }

  function formatContent(content: string) {
    // Simple formatting for line breaks and paragraphs
    return content
      .split('\n\n')
      .map(paragraph => paragraph.trim())
      .filter(paragraph => paragraph.length > 0)
      .map(paragraph => `<p class="mb-4">${paragraph.replace(/\n/g, '<br>')}</p>`)
      .join('');
  }
</script>

<svelte:head>
  {#if story}
    <title>{story.title} - YuYu Lolita</title>
    <meta name="description" content={story.excerpt || story.title} />
    {#if story.metaTitle}
      <meta property="og:title" content={story.metaTitle} />
    {/if}
    {#if story.metaDescription}
      <meta property="og:description" content={story.metaDescription} />
    {/if}
    {#if story.thumbnail}
      <meta property="og:image" content={getThumbnailUrl(story.thumbnail)} />
    {/if}
  {:else}
    <title>История - YuYu Lolita</title>
  {/if}
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 to-purple-50">
  <div class="container mx-auto px-4 py-8">
    <!-- Back button -->
    <div class="mb-8">
      <Button variant="outline" on:click={goBack}>
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Назад к историям
      </Button>
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
          <h3 class="text-lg font-medium text-red-800 mb-2">История не найдена</h3>
          <p class="text-red-600 mb-4">{error}</p>
          <Button variant="secondary" on:click={goBack}>
            Вернуться к историям
          </Button>
        </div>
      </div>
    {:else if story}
      <!-- Story content -->
      <article class="max-w-4xl mx-auto">
        <!-- Header -->
        <header class="text-center mb-12">
          <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
            {story.title}
          </h1>
          
          <div class="flex items-center justify-center space-x-6 text-gray-600 mb-8">
            {#if story.author}
              <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span class="font-medium text-pink-600">{story.author.name}</span>
              </div>
            {/if}
            
            <div class="flex items-center">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>{formatDate(story.publishedAt || story.createdAt)}</span>
            </div>
          </div>
          
          {#if story.excerpt}
            <div class="text-xl text-gray-600 leading-relaxed max-w-2xl mx-auto">
              {story.excerpt}
            </div>
          {/if}
        </header>

        <!-- Featured image -->
        {#if story.thumbnail}
          <div class="mb-12">
            <div class="relative h-64 md:h-96 bg-gradient-to-br from-pink-100 to-purple-100 rounded-2xl overflow-hidden shadow-2xl">
              <img 
                src={getThumbnailUrl(story.thumbnail)} 
                alt={story.title}
                class="w-full h-full object-cover"
              />
              <div class="absolute inset-0 bg-black/10"></div>
            </div>
          </div>
        {/if}

        <!-- Content -->
        <div class="prose prose-lg max-w-none">
          <div class="bg-white rounded-2xl shadow-lg p-8 md:p-12">
            <div class="text-gray-700 leading-relaxed">
              {@html formatContent(story.content)}
            </div>
          </div>
        </div>

        <!-- Additional images -->
        {#if story.images && story.images.length > 0}
          <div class="mt-12">
            <h3 class="text-2xl font-bold text-gray-900 mb-6 text-center">Дополнительные изображения</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              {#each story.images as image}
                <div class="relative h-64 bg-gradient-to-br from-pink-100 to-purple-100 rounded-xl overflow-hidden shadow-lg">
                  <img 
                    src={getImageUrl(image)} 
                    alt="Дополнительное изображение для {story.title}"
                    class="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                  <div class="absolute inset-0 bg-black/10 hover:bg-black/20 transition-colors duration-300"></div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Footer -->
        <footer class="mt-16 text-center">
          <div class="bg-gradient-to-r from-pink-50 to-purple-50 rounded-2xl p-8">
            <h3 class="text-2xl font-bold text-gray-900 mb-4">Понравилась история?</h3>
            <p class="text-gray-600 mb-6">
              Читайте больше интересных историй о японской моде и культуре
            </p>
            <Button variant="primary" size="lg" on:click={goBack}>
              Читать еще истории
            </Button>
          </div>
        </footer>
      </article>
    {/if}
  </div>
</div>

<style>
  :global(.prose p) {
    margin-bottom: 1rem;
    line-height: 1.8;
  }
  
  :global(.prose p:last-child) {
    margin-bottom: 0;
  }
</style>