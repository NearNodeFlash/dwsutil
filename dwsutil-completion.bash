#!/usr/bin/env bash

# Source this file:       . dwsutil-completion.bash
# Then map the commands:  complete -o nospace -F _comp_dwsutil dwsutil.py

_comp_dwsutil()
{
	argfull=$2
        arg="${argfull::5}"

	if [[ "$3" == "--context" ]]
	then
#		echo ""
#		echo "C: ${COMP_CWORD}"
#		echo "W: ${COMP_WORDS}"
#		echo ""
#		for w in ${COMP_WORDS[@]}; do
#			echo "WORD: ${w}"
#		done
		case "${arg}" in
		"w") 
			COMPREPLY+=("wfr")  
			;;
		"i") 
			COMPREPLY+=("inventory")  
			;;
		"st"|"sto") 
			COMPREPLY+=("storage")  
			;;
		"sy"|"sys") 
			COMPREPLY+=("system")  
			;;
		"s") 
			COMPREPLY+=("storage")  
			COMPREPLY+=("system")  
			;;
		"") 
			COMPREPLY+=("wfr")  
			COMPREPLY+=("inventory")  
			COMPREPLY+=("storage")  
			COMPREPLY+=("system")  
			;;
		esac
	elif [[ "$3" == "--operation" ]]
	then
		context="wfr"
		prevword=""
		for w in ${COMP_WORDS[@]}; do
			if [[ "$prevword" == "--context" ]]; then
				context=${w}
			fi
			prevword=${w}
		done
		condition="${context::2}-${arg::1}"
		case "${condition}" in
		"wf-") 
			COMPREPLY+=("assigncomputes")  
			COMPREPLY+=("assignservers")
			COMPREPLY+=("create")  
			COMPREPLY+=("delete")  
			COMPREPLY+=("get")  
			COMPREPLY+=("investigate")  
			COMPREPLY+=("list")  
			COMPREPLY+=("progress")  
			COMPREPLY+=("progressteardown")  
			;;
		"wf-a") 
            if [[ ${#argfull} -le 6 ]] || [[ "${argfull}" =~ .*"assignc".* ]]; then
			    COMPREPLY+=("assigncomputes")  
            fi
            if [[ ${#argfull} -le 6 ]] || [[ "${argfull}" =~ .*"assigns".* ]]; then
	    		COMPREPLY+=("assignservers")
            fi
			;;
		"wf-c") 
			COMPREPLY+=("create")  
			;;
		"wf-d") 
			COMPREPLY+=("delete")  
			;;
		"wf-g") 
			COMPREPLY+=("get")  
			;;
		"wf-i") 
			COMPREPLY+=("investigate")  
			;;
		"wf-l") 
			COMPREPLY+=("list")  
			;;
		"wf-p") 
#			echo "ARG [$arg] [${arg::9}]"
			if [[ "${argfull::9}" == "progresst" ]]; then
				COMPREPLY+=("progressteardown")  
			else
				COMPREPLY+=("progress")  
				COMPREPLY+=("progressteardown")  
			fi
			;;
		"in-"|"in-s") 
			COMPREPLY+=("show")  
			;;
		"st-"|"st-l") 
			COMPREPLY+=("list")  
			;;
		"sy-"|"sy-i") 
			COMPREPLY+=("investigate")  
			;;
		esac
	else
		case "${arg}" in
		"--c"|"--co") 
			COMPREPLY+=("--context")  
			;;
		"--e"|"--ex") 
			COMPREPLY+=("--exr")  
			COMPREPLY+=("--exc")  
			;;
		"--m"|"--mu") 
			COMPREPLY+=("--munge")  
			;;
		"--r"|"--re") 
			COMPREPLY+=("--regex")  
			;;
		"--s"|"--sh"|"--sho") 
			COMPREPLY+=("--showconfig")  
			;;
		"--p"|"--pr") 
			COMPREPLY+=("--pretty")  
			;;
		"--a"|"--al"|"--all") 
			COMPREPLY+=("--alloc")  
			;;
		"--ope") 
			COMPREPLY+=("--operation")  
			;;
		"--opc") 
			COMPREPLY+=("--opcount")  
			;;
		"--o"|"--op") 
			COMPREPLY+=("--operation")  
			COMPREPLY+=("--opcount")  
			;;
		"--nam") 
			COMPREPLY+=("--name")  
			;;
		"--not") 
			COMPREPLY+=("--notimestamp")  
			;;
		"--nod") 
			COMPREPLY+=("--node")  
			;;
		"--nor") 
			COMPREPLY+=("--node")  
			;;
		"--no") 
			COMPREPLY+=("--node")  
			COMPREPLY+=("--notimestamp")  
			COMPREPLY+=("--noreuse")  
			;;
		"--n") 
			COMPREPLY+=("--name")  
			COMPREPLY+=("--node")  
			COMPREPLY+=("--notimestamp")  
			COMPREPLY+=("--noreuse")  
			;;
		"--")
			COMPREPLY+=("--alloc")  
			COMPREPLY+=("--config")  
			COMPREPLY+=("--exc")  
			COMPREPLY+=("--exr")  
			COMPREPLY+=("--inventory")  
			COMPREPLY+=("--jobid")  
			COMPREPLY+=("--kcfg")  
			COMPREPLY+=("--kctx")  
			COMPREPLY+=("--munge")  
			COMPREPLY+=("--name")  
			COMPREPLY+=("--node")  
			COMPREPLY+=("--notimestamp")  
			COMPREPLY+=("--opcount")  
			COMPREPLY+=("--pretty")  
			COMPREPLY+=("--regex")  
			COMPREPLY+=("--noreuse")  
			COMPREPLY+=("--showconfig")  
			COMPREPLY+=("--userid")  
			COMPREPLY+=("--version")  
			COMPREPLY+=("--wlmid")  
			COMPREPLY+=("--context")  
			COMPREPLY+=("--operation")  
			;;
		*)
			if [[ "$3" == "-n" ]]; then
				config=""
				kconfig=""
				prevword=""
				for w in ${COMP_WORDS[@]}; do
					if [[ "$prevword" == "-k" ]] || [[ "$prevword" == "--kcfg" ]]; then
						kconfig="${w}"
					fi
					if [[ "$prevword" == "-c" ]] || [[ "$prevword" == "--config" ]]; then
						config="${w}"
					fi
					prevword=${w}
				done
				if [[ "$config" != "" ]] && [[ "$kconfig" == "" ]]; then
					kconfig=`grep "config:\s*[^\s]" $config 2>/dev/null | awk '{print $2}'`
				fi
				if [[ "$kconfig" != "" ]]; then
					kconfig=`realpath $kconfig`
					export KUBECONFIG=$kconfig
				fi
				if [[ "$2" != "" ]]; then
					result=`kubectl get workflows |grep $2 | awk '{print $1}'`
				else
					result=`kubectl get workflows |grep -v NAME | awk '{print $1}'`
				fi
				if [ $? -ne 0 ] || [ "$result" == "" ]; then
					COMPREPLY+=("<error pulling workflows>")  
				else
					for names in $result; do
						COMPREPLY+=($names)  
					done
				fi
			fi
			;;
		esac
	fi
}
