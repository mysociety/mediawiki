TF_STATE_BUCKET ?= mysociety-generic-tfstate
TF_STATE_KEY ?= wiki-mysociety-org

.PHONEY: clean init plan apply destroy

clean:
	@echo "==> Removing state"
	rm -fr .terraform/

init: clean
	@echo "==> Initialising and configuring remote state"
	terraform init -backend-config="bucket=$(TF_STATE_BUCKET)" -backend-config="key=$(TF_STATE_KEY).tfstate"

plan: init
	@echo "==> Running plan"
	terraform plan -var="bucket_domain_name=$(TF_STATE_KEY)"

apply: plan
	@echo "==> Running apply"
	terraform apply -var="bucket_domain_name=$(TF_STATE_KEY)"

destroy:
        @echo "==> Disabled for this deployment"
