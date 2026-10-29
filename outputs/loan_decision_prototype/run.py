"""Interactive launcher: key stays in process memory, not source code or shell history."""
import getpass,os
if __name__=='__main__':
    print('Team 12 loan prototype — synthetic demo applicants only.')
    if not os.environ.get('OPENROUTER_API_KEY'):
        key=getpass.getpass('OpenRouter API key (hidden; Enter skips LLM generation): ').strip()
        if key:os.environ['OPENROUTER_API_KEY']=key
    from app import main
    main()
