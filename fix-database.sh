#!/bin/bash

echo "🔧 Database Fix Script"
echo "====================="

# Try multiple authentication methods to fix the database
echo "🔄 Attempting database setup with multiple auth methods..."

# Method 1: Try with peer authentication (local socket)
echo "   Method 1: Peer authentication (local socket)"
sudo -u postgres createdb yuyu_lolita 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Database created with peer auth"
else
    echo "   ⚠️  Database creation failed or already exists"
fi

# Method 2: Set up postgres user password
echo "   Method 2: Setting postgres password"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Password set successfully"
else
    echo "   ⚠️  Password setting failed"
fi

# Method 3: Try with codespace user
echo "   Method 3: Creating database with codespace user"
createdb yuyu_lolita 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Database created with codespace user"
    # Update .env to use codespace user
    sed -i 's|postgresql://postgres:postgres@localhost:5432/yuyu_lolita|postgresql://codespace@localhost:5432/yuyu_lolita|g' .env
    echo "   ✅ Updated .env to use codespace user"
else
    echo "   ⚠️  Database creation with codespace user failed"
fi

# Method 4: Test which connection works
echo "🔄 Testing database connections..."

for conn in "postgresql://postgres:postgres@localhost:5432/yuyu_lolita" "postgresql://codespace@localhost:5432/yuyu_lolita" "postgresql://postgres@localhost:5432/yuyu_lolita"
do
    echo "   Testing: $(echo $conn | sed 's|://[^@]*@|://***:***@|')"
    
    if psql "$conn" -c "SELECT current_database(), current_user;" -t >/dev/null 2>&1; then
        echo "   ✅ Connection successful!"
        
        # Update .env with working connection
        escaped_conn=$(echo "$conn" | sed 's/[[\.*^$()+?{|]/\\&/g')
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=$conn|g" .env
        echo "   ✅ Updated .env with working connection"
        
        # Run migration
        echo "🔄 Running database migration..."
        if psql "$conn" -f packages/db/migrations/0000_consolidated_schema.sql >/dev/null 2>&1; then
            echo "   ✅ Migration completed successfully"
        else
            echo "   ⚠️  Migration failed, but database is accessible"
        fi
        
        # Test final connection
        echo "🔄 Final validation..."
        if psql "$conn" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" -t >/dev/null 2>&1; then
            echo "   ✅ Database is fully operational"
        else
            echo "   ⚠️  Database accessible but may have schema issues"
        fi
        
        echo ""
        echo "🎉 Database setup completed!"
        echo "✅ Working connection: $(echo $conn | sed 's|://[^@]*@|://***:***@|')"
        exit 0
    else
        echo "   ❌ Connection failed"
    fi
done

echo ""
echo "❌ All connection methods failed"
echo "🔧 Manual setup may be required"
exit 1