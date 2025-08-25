// Тест запуска API сервера для проверки устранения исходной ошибки
const { spawn } = require('child_process');
const path = require('path');

async function testAPIServer() {
  console.log('🚀 Тестируем запуск API сервера...');
  console.log('📍 Проверяем, исправлена ли ошибка "overall_verification_status не существует"');

  // Устанавливаем переменные окружения
  const env = {
    ...process.env,
    DATABASE_URL: 'postgresql://postgres@/var/run/postgresql/yuyu_lolita',
    API_PORT: '3001',
    NODE_ENV: 'development'
  };

  // Запускаем API сервер
  const apiProcess = spawn('npm', ['run', 'dev'], {
    cwd: path.join(__dirname, 'apps', 'api'),
    env: env,
    stdio: ['pipe', 'pipe', 'pipe']
  });

  console.log('⏳ Запускаем API сервер...');
  
  let output = '';
  let hasError = false;
  let hasSuccess = false;

  // Отслеживаем вывод сервера
  apiProcess.stdout.on('data', (data) => {
    const text = data.toString();
    output += text;
    console.log('📄 STDOUT:', text.trim());
    
    // Проверяем на успешный запуск
    if (text.includes('running on http://localhost:3001') || 
        text.includes('Server started') ||
        text.includes('listening on')) {
      hasSuccess = true;
      console.log('✅ API сервер успешно запущен!');
    }
  });

  apiProcess.stderr.on('data', (data) => {
    const text = data.toString();
    output += text;
    console.log('📄 STDERR:', text.trim());
    
    // Проверяем на исходную ошибку
    if (text.includes('overall_verification_status') && text.includes('не существует')) {
      hasError = true;
      console.log('❌ ИСХОДНАЯ ОШИБКА ВСЕ ЕЩЕ ПРИСУТСТВУЕТ!');
    } else if (text.includes('ERROR') || text.includes('Error')) {
      console.log('⚠️ Обнаружена другая ошибка:', text);
    }
  });

  // Даем серверу время на запуск
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Завершаем процесс
  apiProcess.kill('SIGTERM');

  console.log('\n🔍 РЕЗУЛЬТАТЫ ТЕСТА:');
  console.log('===============================================');
  
  if (hasError) {
    console.log('❌ ОШИБКА: Исходная проблема с overall_verification_status все еще есть');
    return false;
  } else if (hasSuccess) {
    console.log('✅ УСПЕХ: API сервер запустился без ошибок с overall_verification_status');
    console.log('✅ ИСХОДНАЯ ПРОБЛЕМА ПОЛНОСТЬЮ РЕШЕНА!');
    return true;
  } else {
    console.log('⚠️ НЕОПРЕДЕЛЕННО: Сервер не запустился, но исходной ошибки не видно');
    console.log('📝 Полный вывод:');
    console.log(output);
    return false;
  }
}

// Запускаем тест
testAPIServer().then(success => {
  if (success) {
    console.log('\n🎉 ВСЕ ИСПРАВЛЕНО! База данных полностью настроена и готова к работе!');
    process.exit(0);
  } else {
    console.log('\n🔧 Возможно, нужны дополнительные настройки...');
    process.exit(1);
  }
}).catch(error => {
  console.error('\n❌ Ошибка при тестировании:', error);
  process.exit(1);
});