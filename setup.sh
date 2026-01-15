#!/bin/bash

# Script d'installation et de configuration du dashboard
# Usage: ./setup.sh

echo "🚀 Configuration du Dashboard Monitoring AWS Batch"
echo "=================================================="
echo ""

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    echo "💡 Installez Python 3 : brew install python3"
    exit 1
fi

echo "✅ Python 3 détecté : $(python3 --version)"
echo ""

# Vérifier si pip est installé
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé"
    exit 1
fi

echo "✅ pip3 détecté"
echo ""

# Installer les dépendances Python
echo "📦 Installation des dépendances Python..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dépendances Python installées"
else
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi

echo ""

# Vérifier si AWS CLI est installé
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI n'est pas installé"
    echo ""
    echo "💡 Pour installer AWS CLI :"
    echo "   brew install awscli"
    echo ""
    echo "Voulez-vous installer AWS CLI maintenant ? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command -v brew &> /dev/null; then
            brew install awscli
        else
            echo "❌ Homebrew n'est pas installé"
            echo "💡 Installez Homebrew : /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    else
        echo "⏭️  Installation d'AWS CLI ignorée"
        echo "⚠️  Vous devrez l'installer manuellement pour continuer"
        exit 0
    fi
fi

echo "✅ AWS CLI détecté : $(aws --version)"
echo ""

# Vérifier si AWS est configuré
if ! aws sts get-caller-identity &> /dev/null; then
    echo "⚠️  AWS CLI n'est pas configuré"
    echo ""
    echo "💡 Configuration d'AWS CLI..."
    echo "   Vous aurez besoin de :"
    echo "   - Access Key ID"
    echo "   - Secret Access Key"
    echo ""
    echo "Voulez-vous configurer AWS CLI maintenant ? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        aws configure
    else
        echo "⏭️  Configuration AWS ignorée"
        echo "⚠️  Vous devrez exécuter 'aws configure' manuellement"
        exit 0
    fi
fi

echo "✅ AWS CLI configuré"
echo ""

# Tester la connexion à DynamoDB
echo "🧪 Test de connexion à DynamoDB..."
python3 test_dynamo.py

echo ""
echo "=================================================="
echo "✅ Configuration terminée !"
echo ""
echo "💡 Prochaines étapes :"
echo "   1. Si les tests sont passés, lancez le dashboard :"
echo "      streamlit run app.py"
echo ""
echo "   2. Si les tests ont échoué, consultez README_SETUP.md"
echo "=================================================="

